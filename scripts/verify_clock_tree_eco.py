#!/usr/bin/env python3
"""Check the clock ECO's actual geometry, independent LVS and all new evidence."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import klayout.db as db
from check_toolchain import ROOT, verify
from validate_route_candidate import non_top_cell_inventory, region_map, report_markers, pin_layer_map
from prune_route_vias import connectivity
sys.path.insert(0,str(ROOT/'tools/APRtools/apr'))
import rules


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    verify(); d=ROOT/'experiments/a_clock_tree'; b=d/'build'
    st=next(ast.literal_eval(n.value) for n in ast.parse((d/'config.py').read_text()).body
            if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CLOCK_ECO' for t in n.targets))
    source=ROOT/st['source_gds']; dest=b/'candidate.gds'
    assert sha(source)==st['source_sha256']
    old=db.Layout();old.read(str(source));new=db.Layout();new.read(str(dest))
    ot=old.cell('ishi_vga_core');nt=new.cell('ishi_vga_core')
    assert old.dbu==new.dbu==.001 and ot.bbox()==nt.bbox()
    assert non_top_cell_inventory(old,ot.name)==non_top_cell_inventory(new,nt.name)
    manifest=json.loads((b/'manifest.json').read_text())
    assert manifest['gds_sha256']==sha(dest)
    assert all(sha(ROOT/p)==h for p,h in manifest['input_hashes'].items())
    def insts(top): return Counter((i.cell.name,i.trans.to_s()) for i in top.each_inst() if not i.cell.name.startswith('via_'))
    expected=insts(ot)
    for r in manifest['replacements']:
        t=db.Trans(round(r['x']/.001),round(r['y']/.001)).to_s()
        expected[('FILL3',t)]-=1;expected[('BUF_X2',t)]+=1
    assert +expected==insts(nt)
    a,c=region_map(old,ot),region_map(new,nt)
    changed=[k for k in sorted(a.keys()|c.keys()) if not(a.get(k,db.Region())^c.get(k,db.Region())).is_empty()]
    # region_map is recursive: new cell device layers are expected; instances
    # were independently restricted to the four library-identical replacements.
    for li in old.layer_indexes():
        info=old.get_info(li);pair=(info.layer,info.datatype)
        if pair in (rules.M1,rules.M2,rules.V1):continue
        assert (db.Region(ot.shapes(li)) ^ db.Region(nt.shapes(new.layer(*pair)))).is_empty(), pair
    def labels(ly,top):
        return sorted((ly.get_info(li).to_s(),s.text.string,s.text.trans.to_s())
                      for li in ly.layer_indexes() for s in top.shapes(li).each() if s.is_text())
    assert labels(old,ot)==labels(new,nt)
    pins=json.loads((b/'pins.json').read_text());pl,place,lef=pin_layer_map(d/'layout/placement.json')
    connection=connectivity(new,nt,pins,pl)
    assert not connection['pairs'] and not connection['missing'] and not connection['opens']
    assert connection['power_component_counts']=={'vss':1,'vdd':1}
    assert connection['rail_signal_nets']=={'vss':[],'vdd':[]}
    audit=json.loads((b/'audit/metal_connectivity.json').read_text())
    assert audit['placement_instances_matched_to_actual_gds']==345
    assert audit['actual_pin_shapes_labeled']==audit['placement_signal_pin_count']==704
    assert audit['open_net_count']==audit['missing_actual_pin_count']==audit['actual_short_net_pair_count']==0
    assert not report_markers(b/'drawing.lyrdb')
    assert report_markers(b/'candidate_mdp.lyrdb')==report_markers(ROOT/'release/ishi_vga_grid_power_core/experiments/a_power_escape/build/candidate_mdp.lyrdb')
    assert 'strict port mode' in (b/'lvs.log').read_text()
    lvs=db.LayoutVsSchematic();lvs.read(str(b/'core.lvsdb'));x=lvs.xref();count=0;top_pair=None
    for p in x.each_circuit_pair():
        assert p.first() and p.second() and p.status()==x.Match;count+=1
        if p.first().name==nt.name:top_pair=p
    assert top_pair
    ports=[]
    for p in x.each_pin_pair(top_pair):
        assert p.status()==x.Match and p.first() and p.second()
        assert p.first().name().lower()==p.second().name().lower();ports.append(p.first().name().lower())
    assert sorted(ports)==sorted(['clk','r','g','b','hsync','vsync','vdd','vss'])
    assert all(p.status()==x.Match for p in x.each_net_pair(top_pair))
    assert all(p.status()==x.Match for p in x.each_subcircuit_pair(top_pair))
    sta=json.loads((d/'out/STA_ishi_vga_core.guard.json').read_text());assert sta['status']=='PASS'
    functional=json.loads((b/'functional_verification.json').read_text());assert functional['status']=='PASS'
    extraction=json.loads((b/'extraction_manifest.json').read_text())
    assert extraction['gds_sha256']==sha(dest) and extraction['raw_sha256']==sha(b/'core.extracted')
    assert all(sha(ROOT/p)==h for p,h in extraction['hashes'].items())
    assert extraction['simulation_sha256']==sha(b/'core_sim.spice')
    assert extraction['no_combine'] and extraction['hierarchical_device_count']==1790
    cases={}
    for name in ['upper_init','lower_init','vsync_init','frame_wrap_init','powerup','upper_reference']:
        r=json.loads((b/name/'verification.json').read_text());assert r['status']=='PASS'
        assert all(sha(ROOT/p)==h for p,h in r['hashes'].items());cases[name]=r['output_cycles_checked']
    assert sum(v for k,v in cases.items() if k!='upper_reference')==668
    # Capacity values come from the pinned Liberty, not a locally edited limit.
    lib=(ROOT/'tools/APRtools/stdcell/v59_4/tr1um_typ_5v0_25c.lib').read_text()
    def celltext(cell): return lib.split('  cell ('+cell+') {',1)[1].split('  cell (',1)[0]
    ck=float(re.search(r'pin \(CK\).*?capacitance\s*:\s*([\d.]+)',celltext('DFF'),re.S)[1])
    bc=float(re.search(r'pin \(A\).*?capacitance\s*:\s*([\d.]+)',celltext('BUF_X2'),re.S)[1])
    lim=float(re.search(r'max_capacitance\s*:\s*([\d.]+)',celltext('BUF_X2'))[1])
    rootlim=float(re.search(r'max_capacitance\s*:\s*([\d.]+)',celltext('BUFTH'))[1])
    caps={'clk_buf':{'loads':4,'pin_ff':4*bc,'limit_ff':rootlim}}
    for ri,row in enumerate(place['rows']):
        n=sum(i['type']=='DFF' for i in row);caps[f'clk_row{ri}']={'loads':n,'pin_ff':n*ck,'limit_ff':lim}
    for v in caps.values():v['remaining_for_wire_ff']=v['limit_ff']-v['pin_ff'];assert v['remaining_for_wire_ff']>0
    paths=[dest,source,d/'config.py',d/'clock_electrical.tcl',d/'clock_report.tcl',d/'layout/placement.json',d/'out/ishi_vga_core_pnr.v',d/'out/STA_ishi_vga_core.guard.json',Path(__file__),ROOT/'scripts/clock_tree_eco.py',ROOT/'scripts/sta_guard.py',ROOT/'scripts/sta_guard.tcl',ROOT/'scripts/run_apr.py',ROOT/'toolchain.lock.json']
    paths += [b/f for f in ['manifest.json','drawing.lyrdb','candidate_mdp.lyrdb','drc.log','core.lvsdb','lvs.log','ishi_vga_core.spice','reference.log','pins.json','sta.log','functional_verification.json','exhaustive.log','rtl.log','gates.log','observed.hex','audit/metal_connectivity.json','core.extracted','extraction_manifest.json','reference_manifest.json']]
    paths += [b/n/'verification.json' for n in cases]
    result={'status':'CORE_ECO_VERIFIED_NOT_MANUFACTURING_SIGNOFF','gds_sha256':sha(dest),'size_um':[1792.8,897.2],'logical_cells':213,'placement_cells':345,'signal_pins':704,'drawing_drc':0,'mask_warnings':1,'strict_lvs':'PASS','lvs_circuits':count,'lvs_top_nets':len(list(x.each_net_pair(top_pair))),'lvs_top_subcircuits':len(list(x.each_subcircuit_pair(top_pair))),'ports':ports,'short_pairs':0,'open_nets':0,'clock_pin_loads':caps,'sta':sta,'spice_cycles':cases,'extracted_devices':1790,'changes':manifest['replacements'],'limitations':['frame/pads/ESD integration remains paused','no interconnect RC or PVT signoff','one unchanged CLK Floating SG warning','external I/O load and operating range remain to be finalized'],'hashes':{str(p.relative_to(ROOT)):sha(p) for p in paths}}
    (b/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='hashes'},indent=2))


if __name__=='__main__':main()
