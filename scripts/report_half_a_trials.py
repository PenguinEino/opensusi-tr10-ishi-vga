#!/usr/bin/env python3
"""Record this generation of A half-slot attempts, including failed builds.

Do not extend the old half_slot_results.json silently: it is a frozen comparison
snapshot. This report distinguishes exact RGB111/black A from palette changes.
"""
import hashlib
import json
import re
from pathlib import Path

import klayout.db as kdb
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LOGIC = ['a_half_a128_black','a_half_a143_x','a_half_a143_x_direct','a_half_a143_y',
         *['a_half_a_bitmap_'+m for m in ['rows','rowcode','rowgray','setclear','toggle','tt']],
         'a_half_a_cover4','a_half_a_cover3','a_half_a_cover2','a_half_a_direct4']
PHYSICAL = ['a_half_a_black_phys6','a_half_a_black_anneal6','a_half_a_direct4_phys5',
            'a_half_a_direct4_phys5s11','a_half_a_direct4_tight5','a_half_a_direct4_anneal5',
            'a_half_a_direct4_repack5']


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    files = {}; logic = []; physical = []
    def keep(p):
        if p.exists(): files[str(p.relative_to(ROOT))] = sha(p)
    for name in LOGIC + PHYSICAL:
        d = ROOT / 'experiments' / name
        if not d.exists(): continue
        manifest = d / 'source_manifest.json'
        if manifest.exists():
            for p, h in json.loads(manifest.read_text())['sha256'].items():
                assert sha(ROOT / p) == h, p
                keep(ROOT / p)
            keep(manifest)
        if name in LOGIC:
            s = (d / 'build/synthesis.log').read_text()
            settings = json.loads((d / 'trial.json').read_text())
            item = {'name': name, 'settings': settings,
                    'rtl': 'PASS' if '[ ok ] tb_rtl  PASS:' in s else 'not passed'}
            m = re.search(r'合計\s+(\d+)\s+([\d,]+) um2', s)
            if s.rstrip().endswith('完了'):
                assert m
                item.update(synthesis='PASS', cells=int(m[1]),cell_area_um2=int(m[2].replace(',','')))
                ver = json.loads((d / 'build/verification.json').read_text())
                assert ver['result'] == 'PASS'
                for p, h in ver['sha256'].items(): assert sha(ROOT / p) == h, p
                item['final_bufth_gate_test'] = ver['result']
            else:
                assert '既に BUFTH が入っている' in s
                item.update(synthesis='FAILED',final_bufth_gate_test='NOT_RUN',
                            reason='ABC mapped an internal BUFTH; pinned insert_bufth.py refused further insertion. No guard bypass.')
            logic.append(item)
        else:
            item = {'name':name,'status':'DIAGNOSTIC_ONLY'}
            p = d / 'build/physical_report.json'
            if p.exists(): item['pipeline'] = json.loads(p.read_text())['steps']
            solve_log=d/'build/solve.log'
            if solve_log.exists() and '入りきらない' in solve_log.read_text():
                item['packing_failure']=solve_log.read_text().strip()
            gds = d / 'build/diagnostic_compacted.gds'
            if gds.exists():
                ly=kdb.Layout();ly.read(str(gds));box=ly.cell('ishi_vga_core').dbbox()
                item.update(width_um=round(box.width(),3),height_um=round(box.height(),3),
                    fits_1800x900_bbox_only=box.width()<=1800 and box.height()<=900)
            audit = d / 'build/audit/metal_connectivity.json'
            if audit.exists():
                a=json.loads(audit.read_text())
                item.update(actual_signal_pins=a['actual_pin_shapes_labeled'],missing=a['missing_actual_pin_count'],
                            opens=a['open_net_count'],short_pairs=a['actual_short_net_pair_count'])
            physical.append(item)
        for f in ['config.py','trial.json','ishi_vga_core.v','ishi_logo.v','tests/expected_frame.hex',
                  'tests/tb_rtl.v','tests/tb_gates.v','build/synthesis.log','build/postbuf.log',
                  'build/verification.json','out/ishi_vga_core_pnr.v','build/reference.png',
                  'build/physical_report.json','build/row_optimization.json','build/diagnostic_compacted.gds',
                  'build/solve.log','build/repack.json','build/assignment.txt',
                  'build/diagnostic_pins.json','build/diagnostic_shapes.json','layout/placement.json',
                  'build/place.log','build/verify_placement.log','build/audit/metal_connectivity.json']:
            keep(d/f)
    # Produce an explicitly simulated preview; observed.hex begins at VSYNC,
    # and must be rotated back before treating it as a top-left-origin image.
    d = ROOT / 'experiments/a_half_a_direct4'
    obs = np.array([int(s,16) for s in (d/'build/observed.hex').read_text().split()],dtype=np.uint8)
    expected = np.array([int(s,16) for s in (d/'tests/expected_frame.hex').read_text().split()],dtype=np.uint8)
    full = np.roll(obs,490*200)
    assert np.array_equal(full,expected)
    assert (d/'tests/expected_frame.hex').read_bytes() == (ROOT/'experiments/a_half_a128_black/tests/expected_frame.hex').read_bytes()
    screen=full.reshape(525,200)[:480,:160]
    rgb=np.stack([((screen>>b)&1)*255 for b in [2,1,0]],axis=-1)
    png=d/'build/gates.png';Image.fromarray(np.repeat(rgb,4,axis=1)).save(png);keep(png)
    preserved=[]
    for name in ['core_escape_snapshot.json','core_routing_snapshot.json','half_slot_results.json']:
        data=json.loads((ROOT/'docs'/name).read_text())
        for p,h in data['files'].items(): assert sha(ROOT/p)==h,p
        preserved.append({'snapshot':name,'unchanged_files':len(data['files'])})
    for p in [Path(__file__),ROOT/'toolchain.lock.json',ROOT/'scripts/half_a_tight_rows.py',
              ROOT/'build/ishi_vga_half_a_diagnostic.gds']:
        keep(p)
    result={'date':'2026-09-25','target_bbox_um':[1800,900],
        'scope':'A half-slot follow-up. External CLK; reset-free; frame integration paused; primary agent only.',
        'synthesis':logic,'physical':physical,'preserved':preserved,'files':files,
        'limitations':'No A half-slot drawing DRC, MDP, LVS, routed timing, pad escapes, or frame signoff. Gate tests are unit-delay and use a test-only initial state.'}
    (ROOT/'docs/half_a_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'logic':[{k:v for k,v in x.items() if k!='settings'} for x in logic],
                      'physical':physical,'preserved':preserved,'file_count':len(files)},indent=2))


if __name__ == '__main__': main()
