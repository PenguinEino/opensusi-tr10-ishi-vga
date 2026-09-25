#!/usr/bin/env python3
"""Bounded redundant-via trials on the composed routed checkpoint.

Only one existing via_1 placement is removed per candidate. The GDS source is
read-only; every candidate and patch manifest is written below the new design.
"""
import argparse, ast, hashlib, json
from pathlib import Path
import klayout.db as db
ROOT=Path(__file__).resolve().parents[1]
DESIGN=ROOT/'experiments/route_next_local'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def settings():
    tree=ast.parse((DESIGN/'config.py').read_text())
    for n in tree.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='METAL_LOCAL_REPAIR' for t in n.targets):
            return ast.literal_eval(n.value)
    raise RuntimeError('METAL_LOCAL_REPAIR missing from config.py')
S=settings()
def make(name):
    if name not in S['via_trials']: raise SystemExit(f'unknown trial {name}')
    src=Path(S['input_gds']); src=src if src.is_absolute() else ROOT/src; expected=S['input_sha256']
    if sha(src)!=expected: raise RuntimeError('source GDS hash mismatch')
    coords=S['via_trials'][name].get('via_centers_um',[S['via_trials'][name].get('xy_um')]); ly=db.Layout();ly.read(str(src));top=ly.cell('ishi_vga_core'); dbu=ly.dbu
    removed=[]
    for x,y in coords:
        hits=[]
        for inst in list(top.each_inst()):
            if not inst.cell.name.startswith('via_1'): continue
            xx=inst.trans.disp.x*dbu; yy=inst.trans.disp.y*dbu
            if abs(xx-x)<0.001 and abs(yy-y)<0.001: hits.append(inst)
        if len(hits)!=1: raise RuntimeError(f'expected one via_1 at {(x,y)}, found {len(hits)}')
        removed.append({'cell':hits[0].cell.name,'center_um':[x,y]}); hits[0].delete()
    outdir=DESIGN/'build'/name
    outdir.mkdir(parents=True,exist_ok=False)
    out=outdir/'candidate.gds';ly.write(str(out))
    patch={'trial':name,'source_gds':str(src.relative_to(ROOT)),'source_sha256':sha(src),'operation':f'delete {len(removed)} selected via_1 instance(s)','removed_vias':removed,'associated_conflicting_nets':S['via_trials'][name]['nets'],'candidate_gds_sha256':sha(out)}
    (outdir/'patch.json').write_text(json.dumps(patch,indent=2)+'\n')
    print(json.dumps(patch,indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('trial',choices=sorted(S['via_trials']));make(ap.parse_args().trial)
