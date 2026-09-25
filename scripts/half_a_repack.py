#!/usr/bin/env python3
"""Reorder a tight five-row partition using unchanged upstream pack_row.

The row solver can find a low-cut partition whose order fragments free TAP
segments. Try deterministic within-row orders, retain every cell, and let the
ordinary upstream packer generate all physical filler/TAP geometry.
"""
import hashlib
import json
import os
import random
import sys
from pathlib import Path
from a_row_placement import ROOT, context, route
from check_toolchain import verify


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    verify()
    src = ROOT / 'experiments/a_half_a_direct4_anneal5'
    dst = ROOT / 'experiments/a_half_a_direct4_repack5'
    assert not dst.exists()
    for sub in ['build','out','tests']: (dst/sub).mkdir(parents=True,exist_ok=True)
    for f in ['ishi_vga_core.v','ishi_logo.v','out/ishi_vga_core_pnr.v','tests/expected_frame.hex']:
        (dst/f).write_bytes((src/f).read_bytes())
    settings = {'source':src.name,'seed':73,'random_trials':128,'order_passes':80,
                'strategy':'upstream order, decreasing width, increasing width, then local shuffles'}
    cfg=(src/'config.py').read_text().replace('finalize(globals())',f'REPACK = {settings!r}\nfinalize(globals())')
    (dst/'config.py').write_text(cfg)
    paths=[Path(__file__),src/'source_manifest.json',src/'config.py',src/'build/assignment.txt',
           ROOT/'scripts/a_row_placement.py',ROOT/'tools/APRtools/apr/place.py',ROOT/'toolchain.lock.json',
           *[dst/f for f in ['config.py','ishi_vga_core.v','ishi_logo.v','out/ishi_vga_core_pnr.v','tests/expected_frame.hex']]]
    (dst/'source_manifest.json').write_text(json.dumps({'source':src.name,'sha256':{
        str(p.relative_to(ROOT)):sha(p) for p in paths}},indent=2)+'\n')
    cfg,place=context(dst)
    cells,macro,width,cellof,net_cells,ports,macro_pin=place.load(cfg.NET_PATH,cfg.CELL_INFO)
    assert macro is None
    result=(src/'build/assignment.txt').read_text().splitlines()
    score,restart=map(int,result[0].split()); names=sorted(width)
    assignment=dict(zip(names,map(int,result[1].split())))
    assert len(assignment)==len(names) and place.cut_cost(assignment,net_cells)==score
    ys,_=cfg.row_y()
    orders,_=place.order_rows(assignment,width,net_cells,ports,ys,cfg.N_ROWS,{},
                            passes=settings['order_passes'],seed=11,prefs={})
    packed=[];report=[];rng=random.Random(settings['seed'])
    for row,order in enumerate(orders):
        trials=[order,sorted(order,key=lambda n:-width[n]),sorted(order,key=lambda n:width[n])]
        for attempt in range(settings['random_trials']):
            sequence=order.copy()
            for i in range(len(sequence)):
                j=rng.randrange(max(0,i-8),min(len(sequence),i+9))
                sequence[i],sequence[j]=sequence[j],sequence[i]
            trials.append(sequence)
        failures=[]
        for attempt,sequence in enumerate(trials):
            try: placed,end=place.pack_row(sequence,width,cellof,cfg.ROW_WIDTH_UM,True,True,cfg.PLACE_FILL_MODE)
            except SystemExit as error:
                failures.append(str(error));continue
            assert sorted(n for _,n,_,_ in placed if n)==sorted(order)
            assert abs(end-cfg.ROW_WIDTH_UM)<1e-6
            packed.append(placed)
            report.append({'row':row,'accepted_attempt':attempt,'failed_attempts':failures})
            break
        else: raise RuntimeError(f'No legal upstream pack for row {row}')
    cross=place.crossings(assignment,net_cells,ports,cfg.N_ROWS)
    info=json.loads(Path(cfg.CELL_INFO).read_text())
    extra={'assign':assignment,'cut':score,'channel_crossings':cross,
           'tap_x':place.tap_positions(cfg.ROW_WIDTH_UM),
           'pri_x':[x for x,_,kind in place.fixed_blocks(cfg.ROW_WIDTH_UM) if kind=='pri'],
           'row_end_x':[cfg.ROW_WIDTH_UM]*cfg.N_ROWS}
    place.dump(4,'fill',packed,ys,None,info,extra)
    (dst/'layout/row_assignment.json').write_text(json.dumps(assignment,indent=2)+'\n')
    (dst/'build/repack.json').write_text(json.dumps({'score':score,'restart':restart,
        'channel_crossings':cross,'rows':report},indent=2)+'\n')
    route(dst)


if __name__=='__main__':
    if os.environ.get('PYTHONHASHSEED')!='0':
        os.environ['PYTHONHASHSEED']='0';os.execv(sys.executable,[sys.executable,*sys.argv])
    main()
