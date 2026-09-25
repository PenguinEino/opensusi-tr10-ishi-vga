#!/usr/bin/env python3
"""Verify whole-row sharing against current B RTL and the approved full frame."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
from check_toolchain import ROOT, verify

def run(args, cwd=ROOT):
    p=subprocess.run([str(x) for x in args],cwd=cwd,text=True,stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT,check=True)
    return p.stdout

verify()
print(run([ROOT/'.venv/bin/python', ROOT/'scripts/reference_frame.py']),end='')
for name in (sys.argv[1:] or ['row_patterns','row_patterns_onehot']):
    if name not in ['row_patterns','row_patterns_onehot']: raise ValueError(name)
    base=ROOT/'experiments'/name
    ref=base/'build/reference.v'
    ref.write_text((ROOT/'rtl/ishi_logo.v').read_text().replace('module ishi_logo(', 'module ishi_logo_reference('))
    exe=base/'build/equivalence.vvp'
    run([ROOT/'.tools/bin/iverilog','-g2012','-s','tb_logo_equivalence','-o',exe,
         ROOT/'tests/tb_logo_equivalence.v',ref,base/'ishi_logo.v'])
    log=run([ROOT/'.tools/bin/vvp',exe])
    assert 'PASS: all 65536' in log and 'FAIL' not in log
    results=[]
    for model,sources in [('rtl',[ROOT/'rtl/ishi_vga_core.v',base/'ishi_logo.v']),
                           ('gates',[base/'out/ishi_vga_core_pnr.v',base/'build/tr1um_cells.v'])]:
        exe=base/f'build/{model}.vvp'
        run([ROOT/'.tools/bin/iverilog','-g2012','-s','tb_vga','-o',exe,ROOT/'tests/tb_vga.v',*sources])
        for freq,half in [(6.3,'79.365079365'),(6.45,'77.519379845')]:
            dump=base/f'build/{model}_{freq}.hex'
            output=run([ROOT/'.tools/bin/vvp',exe,'+HALF_NS='+half,'+DUMP='+str(dump)],base)
            assert 'PASS: 315017 pixel ticks' in output and 'FAIL' not in output
            assert dump.read_bytes()==(ROOT/'tests/expected_frame.hex').read_bytes()
            log+=f'{model} / {freq} MHz\n'+output
            results.append({'model':model,'mhz':freq,'ticks_checked':315017,'result':'PASS'})
    paths=[ROOT/'rtl/ishi_vga_core.v',ROOT/'rtl/ishi_logo.v',base/'ishi_logo.v',base/'out/ishi_vga_core_pnr.v',base/'config.py',ROOT/'config.py']
    result={'variant':name,'whole_logo_equivalence_combinations':65536,'checks':results,
            'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            'limitations':'Unit-delay gate simulation; no parasitic extraction or routed timing.'}
    (base/'build/verification.json').write_text(json.dumps(result,indent=2)+'\n')
    (base/'build/verification.log').write_text(log)
    print(name+'\n'+log)
