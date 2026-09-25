#!/usr/bin/env python3
"""Reorder the adopted grid+5 circuit with pinned APRtools packing/routing.

Each trial is immutable. Only design placement/order settings change; the
netlist and reference frame remain byte-identical to the selected artwork.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
from a_row_placement import ROOT, context, route
from check_toolchain import verify


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--source', default='a_metal_g_power_anneal4')
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--sites', type=int, default=328)
    ap.add_argument('--prl', type=int, default=10)
    ap.add_argument('--span', action='store_true')
    args = ap.parse_args(); verify()
    assert args.name.startswith('a_power_') and '/' not in args.name + args.source
    src = ROOT/'experiments'/args.source; dst = ROOT/'experiments'/args.name
    assert not dst.exists(), 'Never overwrite a measured trial'
    for sub in ('build','out','tests','layout'): (dst/sub).mkdir(parents=True)
    copied = ('ishi_logo.v','ishi_vga_core.v','out/ishi_vga_core_pnr.v','tests/expected_frame.hex','layout/row_assignment.json')
    for f in copied: shutil.copyfile(src/f,dst/f)
    cfg = (src/'config.py').read_text()
    cfg = re.sub(r'^CORE_WIDTH_TRACKS = .*$', f'CORE_WIDTH_TRACKS = {args.sites}', cfg, flags=re.M)
    cfg = re.sub(r'^ROUTING_KNOBS = .*$', f"ROUTING_KNOBS = {dict(PRL_MIN_PINS=args.prl,SPAN_LANE_PACK=args.span)!r}",cfg,flags=re.M)
    settings = dict(source=args.source, order_seed=args.seed, order_passes=120, sites=args.sites,
                    target_um=[1800,900], adopted_art='g_power', frame_integration=False)
    cfg = cfg.replace('finalize(globals())',f'POWER_LAYOUT = {settings!r}\nfinalize(globals())')
    (dst/'config.py').write_text(cfg)
    inputs = [Path(__file__), ROOT/'scripts/a_row_placement.py', ROOT/'toolchain.lock.json',
              src/'config.py', src/'source_manifest.json', dst/'config.py', *[dst/f for f in copied]]
    (dst/'source_manifest.json').write_text(json.dumps({'source':args.source,'sha256':{
        str(p.relative_to(ROOT)):sha(p) for p in inputs}},indent=2)+'\n')
    c,place=context(dst)
    cells,macro,width,cellof,nets,ports,macro_pin=place.load(c.NET_PATH,c.CELL_INFO)
    assert macro is None
    assignment=json.loads((dst/'layout/row_assignment.json').read_text())
    assert set(assignment)==set(width)
    ys,_=c.row_y()
    order,hpwl=place.order_rows(assignment,width,nets,ports,ys,c.N_ROWS,{},
                               passes=settings['order_passes'],seed=args.seed,prefs={})
    packed=[place.pack_row(row,width,cellof,c.ROW_WIDTH_UM,True,True,c.PLACE_FILL_MODE) for row in order]
    assert all(abs(end-c.ROW_WIDTH_UM)<1e-6 for _,end in packed)
    assert sorted(n for row,_ in packed for _,n,_,_ in row if n)==sorted(width)
    extra={'assign':assignment,'cut':place.cut_cost(assignment,nets),
           'channel_crossings':place.crossings(assignment,nets,ports,c.N_ROWS),'hpwl_um':hpwl,
           'tap_x':place.tap_positions(c.ROW_WIDTH_UM),
           'pri_x':[x for x,_,kind in place.fixed_blocks(c.ROW_WIDTH_UM) if kind=='pri'],
           'row_end_x':[end for _,end in packed]}
    place.dump(4,'fill',[row for row,_ in packed],ys,None,json.loads(Path(c.CELL_INFO).read_text()),extra)
    route(dst)


if __name__=='__main__':
    if os.environ.get('PYTHONHASHSEED')!='0':
        os.environ['PYTHONHASHSEED']='0';os.execv(sys.executable,[sys.executable,*sys.argv])
    main()
