#!/usr/bin/env python3
"""Reproducible isolated B placement experiments, preserving root artifacts."""
import argparse, hashlib, json, re, shutil, subprocess, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def make(name, rows, tracks=296, seed=1, restarts=20, pad=1.0, balance=0.02, fill='alternate'):
    design=ROOT/'experiments'/('place_'+name)
    design.mkdir(parents=True, exist_ok=True)
    (design/'out').mkdir(exist_ok=True)
    (design/'build').mkdir(exist_ok=True)
    source=ROOT/'out/ishi_vga_core_pnr.v'
    shutil.copyfile(source,design/'out/ishi_vga_core_pnr.v')
    cfg=(ROOT/'config.py').read_text()
    vals={'N_ROWS':str(rows),'CORE_WIDTH_TRACKS':str(tracks),'CH_HEIGHTS':repr([140.4]+[151.2]*(rows-1)+[162.0]),'ROUTE_CH_HEIGHTS':repr([216.0]+[900.0]*(rows-1)+[216.0]),'PLACE_SEED':str(seed),'PLACE_RESTARTS':str(restarts),'PAD_WEIGHT':str(pad)}
    for k,v in vals.items():cfg=re.sub(r'^'+k+r'\s*=.*$',k+' = '+v,cfg,flags=re.M)
    cfg=cfg.replace('finalize(globals())',f'PLACE_BALANCE_TOL = {balance}\nPLACE_FILL_MODE = {fill!r}\nfinalize(globals())')
    (design/'config.py').write_text(cfg)
    (design/'source_manifest.json').write_text(json.dumps({'source':'out/ishi_vga_core_pnr.v','sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'rows':rows,'tracks':tracks,'seed':seed,'restarts':restarts,'pad_weight':pad,'balance':balance,'fill':fill},indent=2)+'\n')
    return design

def run(design, entry, args=(), log=None):
    cmd=['python3',str(ROOT/'scripts/run_apr.py'),'--design-root',str(design.relative_to(ROOT)),entry,*args]
    start=time.time()
    with (design/'build'/log).open('w') as f:
        result=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        f.write(f'\nELAPSED_SECONDS={time.time()-start:.1f}\nRETURN_CODE={result.returncode}\n')
    return result.returncode

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('name');ap.add_argument('--rows',type=int,default=7);ap.add_argument('--tracks',type=int,default=296);ap.add_argument('--seed',type=int,default=1);ap.add_argument('--restarts',type=int,default=20);ap.add_argument('--pad',type=float,default=1);ap.add_argument('--balance',type=float,default=.02);ap.add_argument('--fill',default='alternate');ap.add_argument('--route',action='store_true');ap.add_argument('--existing',action='store_true');a=ap.parse_args()
    d=ROOT/'experiments'/('place_'+a.name) if a.existing else make(a.name,a.rows,a.tracks,a.seed,a.restarts,a.pad,a.balance,a.fill)
    if not a.existing:
        if run(d,'apr/place.py',log='place.log'):raise SystemExit(1)
        run(d,'apr/verify_placement.py',log='verify_placement.log')
    if a.route:
        if run(d,'apr/route.py',['--to','6'],log='route_step6.log'):raise SystemExit(2)
        run(d,'apr/squeeze_channels.py',['--in-gds','layout/step6/route_step_2_routed_raw.gds','-o','build/diagnostic_compacted.gds','--pin-map-in','layout/pin_map.json','--pin-map-out','build/diagnostic_pins.json','--net-shapes-in','layout/net_shapes.json','--net-shapes-out','build/diagnostic_shapes.json'],log='diagnostic_compaction.log')
    print(d)
