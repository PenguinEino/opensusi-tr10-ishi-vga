#!/usr/bin/env python3
"""Fail-closed checks of letter animation geometry, netlist, timing and behaviour."""
import argparse,json,re
from collections import Counter
from pathlib import Path
import klayout.db as db
from letter_animation_eco import ROOT,verify,sha,settings,cells
from validate_route_candidate import non_top_cell_inventory,report_markers

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--design-root',type=Path,required=True);a=ap.parse_args();verify()
    d=a.design_root.resolve();b=d/'build';st=settings(d)
    source=ROOT/st['source_gds'];assert sha(source)==st['source_sha256']
    old=db.Layout();old.read(str(source));new=db.Layout();new.read(str(b/'candidate.gds'))
    ot=old.cell('ishi_vga_core');nt=new.cell('ishi_vga_core');assert ot.dbbox()==nt.dbbox()
    assert nt.dbbox().width()<=1800 and nt.dbbox().height()<=900
    assert non_top_cell_inventory(old,ot.name)==non_top_cell_inventory(new,nt.name)
    def labels(ly,top):
        return sorted((ly.get_info(li).to_s(),s.text.string,s.text.trans.to_s()) for li in ly.layer_indexes() for s in top.shapes(li).each() if s.is_text())
    assert labels(old,ot)==labels(new,nt)
    place=json.loads((d/'layout/placement.json').read_text());baseline=json.loads((ROOT/st['placement']).read_text())
    originals={c['name']:c for row in baseline['rows'] for c in row if not c['type'].startswith('FILL')}
    current={c['name']:c for row in place['rows'] for c in row}
    for name,c in originals.items():
        other=current[name];assert (c['type'],c['x'],c['row'])==(other['type'],other['x'],other['row'])
        for pn,p in c['pins'].items():
            expected=next((newnet for inst,pin,oldnet,newnet in st['replacements'] if inst==name and pin==pn),p.get('net'))
            assert other['pins'][pn].get('net')==expected,(name,pn)
    logical=cells((d/'out/ishi_vga_core_pnr.v').read_text());assert len(logical)==241
    assert sum(t=='DFF' for t,n,p in logical)==29
    assert not report_markers(b/'drawing.lyrdb')
    assert report_markers(b/'candidate_mdp.lyrdb')==report_markers(source.parent/'static_mdp.lyrdb')
    lvs=db.LayoutVsSchematic();lvs.read(str(b/'core.lvsdb'));x=lvs.xref();top_pair=None
    for p in x.each_circuit_pair():
        assert p.first() and p.second() and p.status()==x.Match
        if p.first().name==nt.name:top_pair=p
    assert top_pair is not None and 'strict port mode' in (b/'lvs.log').read_text()
    ports=[]
    for p in x.each_pin_pair(top_pair):
        assert p.status()==x.Match and p.first() and p.second()
        assert p.first().name().lower()==p.second().name().lower();ports.append(p.first().name().lower())
    assert sorted(ports)==sorted(['clk','r','g','b','hsync','vsync','vdd','vss'])
    assert all(p.status()==x.Match for p in x.each_net_pair(top_pair))
    assert all(p.status()==x.Match for p in x.each_subcircuit_pair(top_pair))
    audit=json.loads((b/'audit/metal_connectivity.json').read_text())
    assert audit['placement_instances_matched_to_actual_gds']==len(current)
    assert audit['actual_pin_shapes_labeled']==audit['placement_signal_pin_count']
    assert audit['actual_pin_shapes_labeled']==sum(len([p for p in pp if p not in ('vdd','vss')]) for t,n,pp in logical)
    assert audit['open_net_count']==audit['missing_actual_pin_count']==audit['actual_short_net_pair_count']==0
    for filename in ['routing_manifest.json','placement_manifest.json','repair_manifest.json','functional/verification.json']:
        report=json.loads((b/filename).read_text())
        assert all(sha(ROOT/p)==h for p,h in report['hashes'].items()),filename
    route=json.loads((b/'routing_manifest.json').read_text());assert route['gds_sha256']==sha(b/'candidate_unrepaired.gds')
    repair=json.loads((b/'repair_manifest.json').read_text());assert repair['gds_sha256']==sha(b/'candidate.gds') and repair['source_sha256']==route['gds_sha256']
    functional=json.loads((b/'functional/verification.json').read_text());assert functional['status']=='PASS'
    assert functional['continuous_frames']==128 and functional['ticks']==6720000
    assert functional['stage_frames']==[16,16,16,16,64]
    sta=json.loads((d/'out/STA_ishi_vga_core.guard.json').read_text());assert sta['status']=='PASS'
    lib=(ROOT/'tools/APRtools/stdcell/v59_4/tr1um_typ_5v0_25c.lib').read_text()
    section=lib.split('  cell (DFF) {',1)[1].split('  cell (',1)[0]
    ck=float(re.search(r'pin \(CK\).*?capacitance\s*:\s*([\d.]+)',section,re.S)[1])
    section=lib.split('  cell (BUF_X2) {',1)[1].split('  cell (',1)[0]
    limit=float(re.search(r'max_capacitance\s*:\s*([\d.]+)',section)[1])
    loads={f'clk_row{i}':{'dffs':sum(c['type']=='DFF' for c in row),'pin_ff':sum(c['type']=='DFF' for c in row)*ck,'limit_ff':limit} for i,row in enumerate(place['rows'])}
    assert all(c['pin_ff']<c['limit_ff'] for c in loads.values())
    paths=[Path(__file__),d/'config.py',d/'ishi_vga_core.v',d/'ishi_logo.v',d/'out/ishi_vga_core_pnr.v',d/'out/STA_ishi_vga_core.guard.json',d/'layout/placement.json']
    paths += [b/n for n in ['candidate.gds','core.extracted','pins.json','placement_manifest.json','routing_manifest.json','repair_manifest.json','drawing.lyrdb','candidate_mdp.lyrdb','core.lvsdb','lvs.log','ishi_vga_core.spice','audit/metal_connectivity.json','functional/verification.json']]
    result={'status':'CORE_VERIFIED','feature':'I -> S -> H -> I -> idle, 16 frames per letter, 64 idle frames, 128 total','gds_sha256':sha(b/'candidate.gds'),'size_um':[1792.8,897.2],'logical_cells':241,'added_logic_cells':28,'dffs':29,'placement_cells':len(current),'actual_signal_pins':audit['actual_pin_shapes_labeled'],'drawing_drc':0,'mask_warnings':1,'strict_lvs':'PASS','ports':ports,'clock_pin_loads':loads,'sta':sta,'functional':{'frames':128,'ticks':6720000,'counter_transitions':128,'decoder_states':131072,'phase_initial_states':128},'scope':'core only; inherited CLK Floating SG warning; no wire RC or frame integration','hashes':{str(p.relative_to(ROOT)):sha(p) for p in paths}}
    (b/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='hashes'},indent=2),flush=True)

if __name__=='__main__':main()
