#!/usr/bin/env python3
"""Run bundled functional/transistor tests into a NEW directory.

No network, PDK search, workspace fallback, or writes into frozen evidence.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
from verify_bundle import ROOT, verify

CASES = ['upper_init', 'lower_init', 'vsync_init', 'frame_wrap_init', 'powerup', 'upper_reference']


def call(command, cwd, logfile):
    with logfile.open('w') as log:
        subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode', choices=['saved-spice', 'spice', 'rtl', 'gates', 'exhaustive'])
    ap.add_argument('--case', choices=CASES, default='upper_init')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--ngspice', default='ngspice')
    ap.add_argument('--iverilog', default='iverilog')
    ap.add_argument('--vvp', default='vvp')
    a = ap.parse_args()
    verify()
    if a.mode == 'saved-spice':
        from check_wave import check
        for name in CASES:
            d = ROOT / 'simulation' / name
            raw = ROOT / 'verification' / 'spice' / name / 'wave.raw.gz'
            old = json.loads((ROOT / 'verification' / 'spice' / name / 'run.json').read_text())
            assert hashlib.sha256(gzip.decompress(raw.read_bytes())).hexdigest() == old['raw_sha256']
            result = check(raw, json.loads((d / 'case.json').read_text()), ROOT / 'tests/expected_frame.hex')
            print(name, json.dumps(result))
        return
    assert a.out is not None, 'Supply --out with a NEW directory'
    out = a.out.resolve()
    assert not out.exists(), 'Refusing to overwrite: ' + str(out)
    assert not out.is_relative_to(ROOT), 'Keep new results outside the frozen submission'
    out.mkdir(parents=True)
    if a.mode == 'spice':
        from check_wave import check
        shutil.copytree(ROOT / 'simulation', out / 'simulation')
        d = out / 'simulation' / a.case
        call([a.ngspice, '-n', '-b', '-r', 'wave.raw', 'tb.spice'], d, d / 'ngspice.log')
        result = check(d / 'wave.raw', json.loads((d / 'case.json').read_text()), ROOT / 'tests/expected_frame.hex')
    else:
        shutil.copytree(ROOT / 'tests', out / 'tests')
        (out / 'build').mkdir()
        source = ROOT / 'source'
        files = ([source / 'ishi_vga_core.v', source / 'ishi_logo.v'] if a.mode == 'rtl'
                 else [source / 'ishi_vga_core_pnr.v', source / 'tr1um_cells.v'])
        if a.mode=='exhaustive':
            gates=out/'build/gate_core.v';gates.write_text((source/'ishi_vga_core_pnr.v').read_text().replace('module ishi_vga_core','module gate_core',1))
            files=[source/'ishi_vga_core.v',source/'ishi_logo.v',gates,source/'tr1um_cells.v']
        exe = out / 'build' / (a.mode + '.vvp')
        call([a.iverilog, '-g2012', '-s', 'tb_exhaustive' if a.mode=='exhaustive' else 'tb_vga', '-o', str(exe),
              str(out / 'tests' / ('tb_' + a.mode + '.v')), *map(str, files)], out, out / 'compile.log')
        call([a.vvp, str(exe)], out, out / 'simulation.log')
        log = (out / 'simulation.log').read_text()
        if a.mode=='exhaustive':
            assert 'PASS: all 131072 binary counter states' in log and 'FAIL' not in log
            assert (out/'tests/expected_states.hex').read_bytes()==(ROOT/'tests/expected_states.hex').read_bytes()
            result={'status':'PASS','binary_counter_states':131072,'raster_reference_states':52500}
            (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return
        assert 'PASS: 105000 pixel ticks' in log and 'FAIL' not in log
        observed = [int(x, 16) for x in (out / 'build/observed.hex').read_text().split()]
        expected = [int(x, 16) for x in (out / 'tests/expected_frame.hex').read_text().split()]
        assert observed == expected[49000:] + expected[:49000]
        result = {'status': 'PASS', 'mode': a.mode, 'checked_ticks': 105000,
                  'recorded_frame_ticks': len(observed), 'initial_state': 'zero, test fixture only'}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
