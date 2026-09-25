#!/usr/bin/env python3
"""Delete only redundant top-level routing vias, with actual-pin + PDK checks."""
import ast
from collections import defaultdict
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from check_toolchain import ROOT, verify
sys.path.insert(0, str(ROOT / 'tools/APRtools/apr'))
import rules
import lef_parser
import klayout.db as db

DESIGN = ROOT / 'experiments/via_prune'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def settings():
    for n in ast.parse((DESIGN/'config.py').read_text()).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id=='VIA_PRUNE' for t in n.targets):
            return ast.literal_eval(n.value)
    raise RuntimeError('missing VIA_PRUNE config')
def markers(path):
    out=set()
    for it in ET.parse(path).getroot().iter('item'):
        vals=tuple(sorted(v.text.strip() for v in it.findall('values/value') if v.text))
        assert vals, 'DRC marker without geometry'
        out.add((it.findtext('category').strip(),vals))
    return out

def connectivity(ly, top, pins, pin_layers):
    # Flatten the extraction graph: anonymous child-circuit names such as $1
    # are not globally unique when probe_net returns a hierarchical local net.
    l2n=db.LayoutToNetlist(top.name,ly.dbu)
    layers={n:db.Region(top.begin_shapes_rec(ly.layer(*getattr(rules,n)))).merged()
            for n in ('M1','M2','V1','GC','CO')}
    for n,r in layers.items():l2n.register(r,n)
    for r in layers.values(): l2n.connect(r)
    for a,b in [('M1','V1'),('V1','M2'),('GC','CO'),('CO','M1')]:l2n.connect(layers[a],layers[b])
    l2n.extract_netlist()
    def node(layer,x,y):
        n=l2n.probe_net(layers[layer],db.Point(round(x/ly.dbu),round(y/ly.dbu)))
        return n.expanded_name() if n else None
    netroots=defaultdict(set); labels=defaultdict(set); missing=[]
    for net,pp in pins.items():
        for inst,pin,x,y in pp:
            n=node(pin_layers[(inst,pin)],x,y)
            if n is None:missing.append([inst,pin])
            else:netroots[net].add(n);labels[n].add(net)
    # Preserve each actual cell's power label connectivity, including isolated
    # components if present in the source; don't just check one reference rail.
    power=defaultdict(set)
    for ir in top.each_inst():
        if ir.cell.name.startswith('via_'):continue
        for sh in ir.cell.shapes(ly.layer(*rules.M1_LBL)).each():
            if sh.is_text() and sh.text.string.lower() in ('vdd','vss'):
                pt=ir.trans*db.Point(sh.text.trans.disp.x,sh.text.trans.disp.y)
                n=node('M1',pt.x*ly.dbu,pt.y*ly.dbu)
                assert n is not None
                power[sh.text.string.lower()].add(n)
    assert not (power['vdd'] & power['vss']), 'Power short'
    rail_labels={r:sorted(set().union(*(labels[n] for n in nn))) for r,nn in power.items()}
    pairs={tuple(sorted(p)) for names in labels.values() for p in itertools.combinations(names,2)}
    return {'missing':missing,'opens':sorted(n for n,rr in netroots.items() if len(rr)>1),
            'pairs':pairs,'groups':sum(len(n)>1 for n in labels.values()),
            'power_component_counts':{r:len(nn) for r,nn in power.items()},'rail_signal_nets':rail_labels}

def main():
    verify();st=settings();build=DESIGN/'build';build.mkdir(exist_ok=True)
    source=ROOT/st['source_gds'];assert sha(source)==st['source_sha256']
    pins=json.loads((ROOT/st['actual_pins']).read_text());shapes=json.loads((ROOT/st['shapes']).read_text())
    lef=lef_parser.parse_lef(ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_cells.lef')
    place=json.loads((ROOT/st['placement']).read_text())
    pin_layers={}
    for row in place['rows']:
        for inst in row:
            for pin,entry in lef[inst['type']]['pins'].items():
                metal=[{'METAL1':'M1','METAL2':'M2'}[r[0]] for r in entry['rects'] if r[0] in ('METAL1','METAL2')]
                if metal:pin_layers[(inst['name'],pin)]=metal[0]
    baseline_markers=markers(ROOT/st['drawing_baseline'])
    ly=db.Layout();ly.read(str(source));top=ly.cell('ishi_vga_core')
    baseline=connectivity(ly,top,pins,pin_layers);current=baseline
    assert len(baseline['pairs'])==143 and not baseline['missing'] and not baseline['opens']
    grouped=defaultdict(list)
    for ir in top.each_inst():
        if ir.cell.name.startswith('via_1'):
            grouped[(ir.trans.disp.x,ir.trans.disp.y)].append(ir.cell_inst)
    candidates=[]
    for pt,instances in grouped.items():
        x,y=(z*ly.dbu for z in pt); owners=set()
        for net,boxes in shapes.items():
            for layer,x0,y0,x1,y1 in boxes:
                e=st['coordinate_tolerance_um']+rules.VIA_PAD/2
                if x0-e<=x<=x1+e and y0-e<=y<=y1+e:
                    owners.add(net);break
        if len(owners)>1:candidates.append((pt,sorted(owners)))
    print(f'Candidate locations: {len(candidates)}',flush=True)
    trials=[];accepted=[]
    for pass_no in range(st['max_passes']):
        count=0
        for pt,owners in candidates:
            refs=[ir for ir in top.each_inst() if ir.cell.name.startswith('via_1') and (ir.trans.disp.x,ir.trans.disp.y)==pt]
            if not refs:continue
            removed=[ir.cell_inst for ir in refs]
            for ir in refs:ir.delete()
            result=connectivity(ly,top,pins,pin_layers)
            improved=(not result['missing'] and not result['opens'] and result['pairs']<current['pairs']
                      and result['power_component_counts']==baseline['power_component_counts']
                      and result['rail_signal_nets']==baseline['rail_signal_nets'])
            rec={'pass':pass_no,'xy_um':[round(v*ly.dbu,4) for v in pt], 'instances':len(refs),'map_owners':owners,
                 'pair_count':len(result['pairs']),'opens':result['opens'],'missing':result['missing'],'accepted':False}
            if improved:
                folder=build/f'trial_{len(trials):03d}';folder.mkdir(exist_ok=True)
                gds=folder/'candidate.gds';report=folder/'drawing.lyrdb';ly.write(str(gds))
                proc=subprocess.run([sys.executable,str(ROOT/'scripts/run_apr.py'),'--design-root',str(DESIGN),
                    'apr/drc_pdk.py',str(gds),'ishi_vga_core','-r',str(report)],text=True,capture_output=True)
                (folder/'drc.log').write_text(proc.stdout+proc.stderr)
                rec.update({'candidate':str(gds.relative_to(ROOT)),'drc_exit':proc.returncode})
                if report.exists() and proc.returncode in (0,1):
                    delta=markers(report)-baseline_markers
                    rec['new_drc_markers']=len(delta)
                    if not delta:
                        rec['accepted']=True;rec['resolved_pairs']=sorted(map(list,current['pairs']-result['pairs']))
                        current=result;count+=1;accepted.append(rec)
                        print(f"Accepted {rec['xy_um']}: pairs={len(current['pairs'])}, groups={current['groups']}",flush=True)
            trials.append(rec)
            if not rec['accepted']:
                for ci in removed:top.insert(ci)
        if not count:break
    dest=build/'via_pruned.gds';ly.write(str(dest))
    def serial(r):return {k:(sorted(map(list,v)) if k=='pairs' else v) for k,v in r.items()}
    manifest={'source':st['source_gds'],'source_sha256':sha(source),'output_sha256':sha(dest),
        'generator_sha256':sha(Path(__file__)),'config_sha256':sha(DESIGN/'config.py'),
        'before':serial(baseline),'after':serial(current),'accepted':accepted,'trials':trials,
        'limitations':'Actual point connectivity and official drawing DRC checked; independent full pin-shape audit, mask DRC and circuit LVS remain separate.'}
    (build/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    assert sha(source)==st['source_sha256']
    print(f"Finished: {len(accepted)} accepted removals, {len(current['pairs'])} pairs",flush=True)
if __name__=='__main__':main()
