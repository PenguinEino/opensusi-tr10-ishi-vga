#!/usr/bin/env python3
"""A core redundant routing-via removal with strict connectivity/DRC guards."""
import argparse
import ast
from collections import defaultdict
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from check_toolchain import ROOT, verify
import prune_route_vias as helpers
from validate_route_candidate import pin_layer_map
import klayout.db as db
import rules


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('name'); a = ap.parse_args()
    assert a.name.startswith('a_') and '/' not in a.name
    verify(); d = ROOT / 'experiments' / a.name
    settings = [ast.literal_eval(n.value) for n in ast.parse((d/'config.py').read_text()).body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id=='VIA_PRUNE' for t in n.targets)]
    assert len(settings)==1; st=settings[0]; build=d/'build'; build.mkdir(exist_ok=True)
    source=ROOT/st['source_gds']; assert sha(source)==st['source_sha256']
    pins=json.loads((ROOT/st['actual_pins']).read_text())
    assert sum(map(len,pins.values()))==st['expected_signal_pins']
    shapes=json.loads((ROOT/st['shapes']).read_text())
    layers,_,_=pin_layer_map(ROOT/st['placement'])
    baseline_markers=helpers.markers(ROOT/st['drawing_baseline'])
    ly=db.Layout();ly.read(str(source));top=ly.cell('ishi_vga_core')
    before=helpers.connectivity(ly,top,pins,layers);current=before
    assert len(before['pairs'])==st['baseline_short_pairs'] and not before['missing'] and not before['opens']
    groups=defaultdict(list)
    for ir in top.each_inst():
        if ir.cell.name.startswith('via_1'):
            groups[(ir.trans.disp.x,ir.trans.disp.y)].append(ir.cell_inst)
    candidates=[]
    for point in groups:
        x,y=(v*ly.dbu for v in point);owners=set()
        for net,boxes in shapes.items():
            for layer,x0,y0,x1,y1 in boxes:
                e=rules.VIA_PAD/2 + st['coordinate_tolerance_um']
                if x0-e<=x<=x1+e and y0-e<=y<=y1+e:
                    owners.add(net);break
        if len(owners)>1:candidates.append((point,sorted(owners)))
    accepted=[];trials=[]
    print(f"Candidates={len(candidates)}; pairs={len(before['pairs'])}",flush=True)
    for pass_no in range(st['max_passes']):
        count=0
        for point,owners in candidates:
            refs=[ir for ir in top.each_inst() if ir.cell.name.startswith('via_1') and
                  (ir.trans.disp.x,ir.trans.disp.y)==point]
            if not refs: continue
            removed=[ir.cell_inst for ir in refs]
            for ir in refs: ir.delete()
            result=helpers.connectivity(ly,top,pins,layers)
            improved=(not result['opens'] and not result['missing'] and result['pairs']<current['pairs'] and
                      result['power_component_counts']==before['power_component_counts'] and result['rail_signal_nets']==before['rail_signal_nets'])
            rec={'xy_um':[round(v*ly.dbu,4) for v in point], 'pass':pass_no, 'owners':owners,
                 'pairs':len(result['pairs']), 'opens':result['opens'], 'missing':result['missing'], 'accepted':False}
            if improved:
                folder=build/f'trial_{len(trials):04d}';folder.mkdir(exist_ok=True)
                gds=folder/'candidate.gds'; report=folder/'drawing.lyrdb'
                opt=db.SaveLayoutOptions();opt.gds2_write_timestamps=False;ly.write(str(gds),opt)
                proc=subprocess.run([sys.executable,str(ROOT/'scripts/run_apr.py'),'--design-root',str(d),
                    'apr/drc_pdk.py',str(gds),'ishi_vga_core','-r',str(report)],text=True,capture_output=True)
                (folder/'drc.log').write_text(proc.stdout+proc.stderr)
                if proc.returncode in (0,1) and report.exists() and not (helpers.markers(report)-baseline_markers):
                    rec['accepted']=True;rec['resolved_pairs']=sorted(map(list,current['pairs']-result['pairs']))
                    current=result;count+=1;accepted.append(rec)
                    print(f"Accepted {rec['xy_um']}: pairs={len(current['pairs'])}, groups={current['groups']}",flush=True)
            if not rec['accepted']:
                for ci in removed:top.insert(ci)
            trials.append(rec)
        if not count:break
    dest=build/'candidate.gds';opt=db.SaveLayoutOptions();opt.gds2_write_timestamps=False;ly.write(str(dest),opt)
    serial=lambda s:{k:(sorted(map(list,v)) if k=='pairs' else v) for k,v in s.items()}
    paths=[Path(__file__),ROOT/'scripts/prune_route_vias.py',ROOT/'scripts/validate_route_candidate.py',
           d/'config.py',ROOT/st['actual_pins'],ROOT/st['shapes'],ROOT/st['placement'],ROOT/'toolchain.lock.json']
    manifest={'before':serial(before),'after':serial(current),'accepted':accepted,'trials':trials,
              'source':st['source_gds'],'source_sha256':sha(source),'gds_sha256':sha(dest),
              'inputs':{str(p.relative_to(ROOT)):sha(p) for p in paths}}
    (build/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Final pairs={len(current["pairs"])}; deleted locations={len(accepted)}',flush=True)


if __name__=='__main__':main()
