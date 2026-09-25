#!/usr/bin/env python3
"""Collect half-slot feasibility evidence; no inferred physical signoff."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

import klayout.db as kdb

ROOT=Path(__file__).resolve().parents[1]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def analyze_states(size,start,step,expected):
    cycle=[];x=start
    while x not in cycle:cycle.append(x);x=step(x)
    assert x==start and len(cycle)==expected
    target=set(cycle);worst=0
    for x in range(size):
        seen=set();n=0
        while x not in target:
            assert x not in seen
            seen.add(x);x=step(x);n+=1
        worst=max(worst,n)
    return worst


def main():
    files={};logic=[];physical=[];startup=[]
    def keep(p):
        if p.exists():files[str(p.relative_to(ROOT))]=sha(p)
    for d in sorted((ROOT/'experiments').glob('a_half_*')):
        manifest=d/'source_manifest.json'
        if manifest.exists():
            for p,h in json.loads(manifest.read_text())['sha256'].items():assert sha(ROOT/p)==h,p
            keep(manifest)
        log=d/'build/synthesis.log'
        if log.exists():
            text=log.read_text();m=re.search(r'合計\s+(\d+)\s+([\d,]+) um2',text)
            assert text.rstrip().endswith('完了') and m,d
            assert 'PASS:' in text and 'FAIL' not in text,d
            settings=json.loads((d/'trial.json').read_text())
            verification=json.loads((d/'build/verification.json').read_text())
            for p,h in verification['sha256'].items():assert sha(ROOT/p)==h,p
            assert verification['result']=='PASS'
            logic.append({'name':d.name,'cells':int(m[1]),'cell_area_um2':int(m[2].replace(',','')),
                          'settings':settings,'rtl':'PASS','post_bufth_gates':'PASS'})
            hm=(1<<settings['h_bits'])-1
            hd=analyze_states(hm+1,settings['h_start'],lambda h:settings['h_start'] if h==settings['h_end'] else (h-1)&hm,settings['horizontal_total'])
            vd=analyze_states(1024,settings['v_start'],lambda v:settings['v_start'] if v==settings['v_last'] else (v+1)&1023,525)
            startup.append({'name':d.name,'all_horizontal_binary_states':hm+1,'all_vertical_binary_states':1024,
                'h_cycle':settings['horizontal_total'],'v_cycle':525,'max_h_steps_into_cycle':hd,
                'max_v_line_steps_into_cycle':vd,'safe_acquisition_bound_ticks':hd+(vd+1)*settings['horizontal_total']+1,
                'scope':'counter transition model only; not a formal proof of RTL or analog startup'})
        gds=d/'build/diagnostic_compacted.gds'
        if gds.exists():
            ly=kdb.Layout();ly.read(str(gds));box=ly.cell('ishi_vga_core').dbbox()
            item={'name':d.name,'width_um':round(box.width(),3),'height_um':round(box.height(),3),
                  'fits_1800x900_bbox_only':box.width()<=1800 and box.height()<=900,'status':'DIAGNOSTIC_ONLY'}
            audit=d/'build/audit/metal_connectivity.json'
            if audit.exists():
                a=json.loads(audit.read_text())
                item.update(pins=a['actual_pin_shapes_labeled'],missing_pins=a['missing_actual_pin_count'],
                            open_nets=a['open_net_count'],short_pairs=a['actual_short_net_pair_count'])
            for kind,f in [('drawing','drawing.lyrdb'),('mdp','diagnostic_compacted_mdp.lyrdb')]:
                p=d/'build'/f
                if p.exists():
                    items=ET.parse(p).getroot().findall('./items/item')
                    item[kind]={'count':len(items),'categories':dict(Counter(i.findtext('category') for i in items))}
            physical.append(item)
        for f in ['config.py','trial.json','ishi_vga_core.v','ishi_logo.v','tests/expected_frame.hex','tests/tb_rtl.v',
                  'tests/tb_gates.v','build/synthesis.log','build/postbuf.log','build/verification.json',
                  'out/ishi_vga_core_pnr.v','layout/placement.json','build/physical_report.json',
                  'build/row_optimization.json','build/diagnostic_compacted.gds','build/diagnostic_pins.json',
                  'build/diagnostic_shapes.json','build/audit/metal_connectivity.json','build/drawing.lyrdb',
                  'build/diagnostic_compacted_mdp.lyrdb','build/drc.log','build/reference.png']:
            keep(d/f)
    for p in [Path(__file__),ROOT/'scripts/half_slot_trial.py',ROOT/'scripts/half_slot_grid_trial.py',ROOT/'scripts/half_slot_black_trial.py',
              ROOT/'scripts/a_row_placement.py',ROOT/'scripts/row_anneal.cpp',ROOT/'toolchain.lock.json']:
        keep(p)
    b=[]
    for name in ['core_escape_snapshot.json','core_routing_snapshot.json']:
        data=json.loads((ROOT/'docs'/name).read_text())
        for p,h in data['files'].items():assert sha(ROOT/p)==h,p
        b.append({'snapshot':name,'files':len(data['files']),'unchanged':True})
    result={'date':'2026-09-25','scope':'half-slot and seven pins excluding common VSS, including VDD; artwork alternatives unadopted',
            'target_bbox_um':[1800,900],'synthesis':logic,'physical':physical,'b_preservation':b,'files':files,
            'limitations':'Only grid black candidate has independent actual-pin audit and official drawing/MDP checks. No half-slot LVS, final pin escapes, frame, routed timing or silicon test.'}
    (ROOT/'docs/half_slot_results.json').write_text(json.dumps(result,indent=2)+'\n')
    (ROOT/'docs/half_slot_startup.json').write_text(json.dumps(startup,indent=2)+'\n')
    print(json.dumps({'synthesis':[(x['name'],x['cells'],x['cell_area_um2']) for x in logic],'physical':physical,'b':b},indent=2))


if __name__=='__main__':main()
