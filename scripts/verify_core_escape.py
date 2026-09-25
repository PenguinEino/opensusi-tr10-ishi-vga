#!/usr/bin/env python3
"""Audit escape-only changes and their fresh official DRC and strict LVS reports."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
import klayout.db as db
from check_toolchain import ROOT, verify
from prune_route_vias import connectivity
from validate_route_candidate import pin_layer_map, non_top_cell_inventory, inst_signature, region_map, report_markers
sys.path.insert(0,str(ROOT/'tools/APRtools/apr'))
import rules


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--design-root',type=Path,required=True)
    ap.add_argument('--reference',type=Path,required=True); a=ap.parse_args(); verify()
    design=a.design_root.resolve(); build=design/'build'; st=None
    for n in ast.parse((design/'config.py').read_text()).body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CORE_ESCAPE' for t in n.targets): st=ast.literal_eval(n.value)
    assert st is not None
    source=ROOT/st['source_gds']; dest=build/'candidate.gds'; mf=build/'manifest.json'
    m=json.loads(mf.read_text()); assert sha(source)==st['source_sha256'] and sha(dest)==m['candidate_sha256']
    assert all(sha(ROOT/p)==h for p,h in m['input_hashes'].items())
    sl=db.Layout();sl.read(str(source));sc=sl.cell(st['top'])
    dl=db.Layout();dl.read(str(dest));dc=dl.cell(st['top']);assert sl.dbu==dl.dbu
    assert inst_signature(sc)==inst_signature(dc)
    assert non_top_cell_inventory(sl,sc.name)==non_top_cell_inventory(dl,dc.name)
    sr,dr=region_map(sl,sc),region_map(dl,dc)
    changed=[list(k) for k in sorted(sr.keys()|dr.keys()) if not (sr.get(k,db.Region())^dr.get(k,db.Region())).is_empty()]
    assert all(tuple(k) in (rules.M1,rules.M2,rules.V1,rules.M1_PIN,rules.M2_PIN) for k in changed)
    pins=json.loads((ROOT/st['actual_pins']).read_text()); pin_layers,_,_=pin_layer_map(ROOT/st['placement'])
    old=connectivity(sl,sc,pins,pin_layers);new=connectivity(dl,dc,pins,pin_layers)
    assert not new['pairs'] and not new['missing'] and not new['opens']
    assert old['power_component_counts']==new['power_component_counts'] and old['rail_signal_nets']==new['rail_signal_nets']
    audit_path=build/'audit/metal_connectivity.json'; audit=json.loads(audit_path.read_text())
    assert audit['placement_instances_matched_to_actual_gds']==421
    assert audit['actual_pin_shapes_labeled']==audit['placement_signal_pin_count']==987
    assert audit['missing_actual_pin_count']==audit['open_net_count']==0
    assert not audit['actual_short_components']
    def labels(ly,top):
        found={}
        for tag in ('M1','M2'):
            for sh in top.shapes(ly.layer(*getattr(rules,tag+'_LBL'))).each():
                if sh.is_text():
                    name=sh.text.string;assert name not in found
                    found[name]=[tag,sh.text.x*ly.dbu,sh.text.y*ly.dbu]
        return found
    before,after=labels(sl,sc),labels(dl,dc)
    assert set(before)==set(after) and len(after)==12
    assert before['vdd']==after['vdd'] and before['vss']==after['vss']
    route_names=[r['net'] for r in m['routes']]
    assert len(route_names)==10 and set(route_names)==set(after)-{'vdd','vss'}
    l2n=db.LayoutToNetlist(dc.name,dl.dbu)
    rr={tag:db.Region(dc.begin_shapes_rec(dl.layer(*getattr(rules,tag)))).merged() for tag in ('M1','M2','V1','CO','GC')}
    for tag,r in rr.items():l2n.register(r,tag);l2n.connect(r)
    for aa,bb in [('M1','V1'),('M2','V1'),('M1','CO'),('GC','CO')]:l2n.connect(rr[aa],rr[bb])
    l2n.extract_netlist();u=lambda x:round(x/dl.dbu)
    for r in m['routes']:
        name=r['net'];tag=r['layer'];x,y=r['xy_um']
        assert after[name][0]==tag and all(abs(a-b)<dl.dbu/2 for a,b in zip(after[name][1:],[x,y]))
        point=db.Point(u(x),u(y));end=l2n.probe_net(rr[tag],point);assert end
        pin_regions=db.Region(dc.shapes(dl.layer(*getattr(rules,tag+'_PIN'))))
        marker=pin_regions.interacting(db.Region(db.Box(point.x,point.y,point.x+1,point.y+1)))
        assert not marker.is_empty() and (marker-rr[tag]).is_empty()
        for inst,pin,px,py in pins[name]:
            node=l2n.probe_net(rr[pin_layers[(inst,pin)]],db.Point(u(px),u(py)))
            assert node and node.expanded_name()==end.expanded_name()
    bbox=dc.dbbox();assert bbox.width()<=st['max_core_size_um'][0] and bbox.height()<=st['max_core_size_um'][1]
    draw=build/'drawing.lyrdb';mask=build/'candidate_mdp.lyrdb'
    dm,mm=report_markers(draw),report_markers(mask)
    assert not dm
    source_mask=source.with_name(source.stem+'_mdp.lyrdb')
    assert mm==report_markers(source_mask)
    log=build/'lvs.log';text=log.read_text()
    assert 'strict port mode' in text and 'flag_missing_ports enabled' in text and 'Congratulations! Netlists match.' in text
    report=build/'core.lvsdb';lvs=db.LayoutVsSchematic();lvs.read(str(report));xref=lvs.xref()
    circuits=[];top=None
    for p in xref.each_circuit_pair():
        assert p.first() and p.second() and p.status()==xref.Match
        circuits.append([p.first().name,p.second().name,str(p.status())])
        if p.first().name==st['top']:top=p
    assert top
    expected=re.search(r'(?im)^\.subckt\s+'+re.escape(st['top'])+r'\s+([^\n]+)',a.reference.read_text())[1].lower().split()
    matched=[]
    for p in xref.each_pin_pair(top):
        assert p.first() and p.second() and p.status()==xref.Match
        assert p.first().name().lower()==p.second().name().lower()
        matched.append(p.first().name().lower())
    assert sorted(matched)==sorted(expected)==sorted(n.lower() for n in after)
    assert all(p.status()==xref.Match for p in xref.each_net_pair(top))
    assert all(p.status()==xref.Match for p in xref.each_subcircuit_pair(top))
    paths=[source,dest,mf,design/'config.py',audit_path,draw,mask,source_mask,report,log,build/'drc.log',
           a.reference.resolve(),Path(__file__).resolve(),ROOT/'tools/APRtools/apr/lvs_pdk.py',
           ROOT/'tools/APRtools/apr/drc_pdk.py',ROOT/'toolchain.lock.json']
    paths+=sorted((ROOT/'tools/TR-1um/libs.tech/klayout/tech/lvs').glob('*.lvs'))
    result={'status':'ACCEPTED','scope':'ten core signal escapes, not pad/frame integration',
        'source_sha256':sha(source),'candidate_sha256':sha(dest),'signal_pins':987,'short_pairs':0,'open_nets':0,
        'power':{k:new[k] for k in ('power_component_counts','rail_signal_nets')},'geometry_layers_changed':changed,
        'stdcell_shapes_and_placement_unchanged':True,'all_escape_labels_and_markers_connected':True,
        'bbox_um':[bbox.left,bbox.bottom,bbox.right,bbox.top],'size_um':[round(bbox.width(),4),round(bbox.height(),4)],
        'drawing_drc':len(dm),'mask_warnings':len(mm),'strict_lvs':'PASS','lvs_circuits':circuits,'lvs_ports':matched,
        'ports':m['routes'],'hashes':{str(p.relative_to(ROOT)):sha(p) for p in paths}}
    (build/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','size_um','short_pairs','open_nets','drawing_drc','mask_warnings','strict_lvs')},indent=2))


if __name__=='__main__':main()
