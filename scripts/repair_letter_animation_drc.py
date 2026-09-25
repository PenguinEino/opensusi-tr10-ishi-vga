#!/usr/bin/env python3
"""Recorded same-net junction fills and a short CLK branch endpoint jog.

Only direct top-level metal boxes change; standard-cell contents and placement
are untouched. Full connectivity is enforced here; official DRC/LVS follow.
"""
import argparse,ast,json,shutil
from pathlib import Path
import klayout.db as db
from letter_animation_eco import ROOT,verify,sha,pinmap,lef_parser,rules
from prune_route_vias import connectivity

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--design-root',type=Path,required=True);a=ap.parse_args();verify()
    d=a.design_root.resolve();b=d/'build'
    st=next(ast.literal_eval(n.value) for n in ast.parse((d/'config.py').read_text()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='LOCAL_REPAIR' for t in n.targets))
    route=json.loads((b/'routing_manifest.json').read_text());src=b/'candidate_unrepaired.gds';dest=b/'candidate.gds'
    if sha(dest)==route['gds_sha256']:shutil.copyfile(dest,src)
    assert sha(src)==route['gds_sha256']
    ly=db.Layout();ly.read(str(src));top=ly.cell('ishi_vga_core');oldbox=top.bbox();u=lambda v:round(v/ly.dbu)
    for tag,*box in st['remove_boxes']:
        li=ly.layer(*getattr(rules,tag));bb=db.Box(*(u(v) for v in box))
        hits=[s for s in top.shapes(li).each() if s.is_box() and s.box==bb];assert len(hits)==1
        top.shapes(li).erase(hits[0])
    for tag,*box in st['add_boxes']:
        assert tag in ('M1','M2');top.shapes(ly.layer(*getattr(rules,tag))).insert(db.Box(*(u(v) for v in box)))
    lef=lef_parser.parse_lef(ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_cells.lef')
    ys=sorted({round(i.trans.disp.y*ly.dbu,4) for i in top.each_inst() if i.cell.name in {c['foreign'] for c in lef.values()}})
    pins,pl=pinmap(json.loads((d/'layout/placement.json').read_text()),lef,ys)
    result=connectivity(ly,top,pins,pl)
    assert not result['pairs'] and not result['opens'] and not result['missing']
    assert result['power_component_counts']=={'vss':1,'vdd':1} and result['rail_signal_nets']=={'vss':[],'vdd':[]}
    assert oldbox==top.bbox()
    save=db.SaveLayoutOptions();save.gds2_write_timestamps=False;ly.write(str(dest),save)
    report={'status':'CONNECTED_NOT_SIGNED_OFF','source_sha256':sha(src),'gds_sha256':sha(dest),'changes':st,'hashes':{str(p.relative_to(ROOT)):sha(p) for p in [src,d/'config.py',Path(__file__),d/'layout/placement.json']}}
    (b/'repair_manifest.json').write_text(json.dumps(report,indent=2)+'\n');print('Connected metal repair',sha(dest),flush=True)

if __name__=='__main__':main()
