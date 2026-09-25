#!/usr/bin/env python3
"""Exhaustive frame checks at RTL and (when present) final synthesis netlist."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from check_toolchain import verify

def run(args):
    p = subprocess.run([str(a) for a in args], cwd=ROOT, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    print(p.stdout, end='')
    return p.stdout

def main():
    verify()
    (ROOT/'build').mkdir(exist_ok=True)
    generated = ROOT/'rtl/ishi_logo.v'
    old = generated.read_bytes()
    run([sys.executable, 'scripts/generate_logo_rtl.py'])
    if old != generated.read_bytes():
        raise RuntimeError('Generated RTL was stale; review updated rtl/ishi_logo.v')
    run([sys.executable, 'scripts/reference_frame.py'])
    cases = {'rtl': ['rtl/ishi_vga_core.v', 'rtl/ishi_logo.v']}
    net = ROOT/'out/ishi_vga_core_pnr.v'
    if net.exists():
        cases['gates'] = [str(net), 'build/tr1um_cells.v']
    records = []
    for name, sources in cases.items():
        exe = f'build/{name}_test.vvp'
        run([ROOT/'.tools/bin/iverilog', '-g2012', '-s', 'tb_vga', '-o', exe,
             'tests/tb_vga.v', *sources])
        for freq, half in [('630', '79.365079365'), ('645', '77.519379845')]:
            dump = f'build/{name}_{freq}.hex'
            log = run([ROOT/'.tools/bin/vvp', exe, '+HALF_NS='+half, '+DUMP='+dump])
            (ROOT/f'build/{name}_{freq}.log').write_text(log)
            if 'PASS: 315017 pixel ticks' not in log or 'FAIL' in log:
                raise RuntimeError(f'{name}/{freq}: missing PASS')
            if (ROOT/dump).read_bytes() != (ROOT/'tests/expected_frame.hex').read_bytes():
                raise RuntimeError('Simulator frame differs from independent reference')
            a=np.loadtxt(ROOT/dump,dtype=np.uint8,converters=lambda s:int(s,16)).reshape(525,200)[:480,:160]
            rgb=np.stack([((a>>4)&3)*85,((a>>2)&3)*85,(a&3)*85],axis=-1)
            Image.fromarray(np.repeat(rgb,4,axis=1)).save(ROOT/f'build/{name}_{freq}.png')
            records.append({'model':name,'clock_mhz':int(freq)/100,'ticks_checked':315017,'result':'PASS'})
    inputs=['rtl/ishi_vga_core.v','rtl/ishi_logo.v','assets/logo_rectangles.json','tests/tb_vga.v']
    if net.exists(): inputs.append(str(net.relative_to(ROOT)))
    report={'variant':'B / 21 rectangles','checks':records,'sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in inputs},
            'limitations':'Gate simulation uses unit delays, not SDF or silicon timing.'}
    (ROOT/'build/verification.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__': main()
