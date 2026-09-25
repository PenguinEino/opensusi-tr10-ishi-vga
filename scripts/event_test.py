#!/usr/bin/env python3
"""Full 6.30/6.45 MHz RTL and final-netlist checks for event_* experiments."""
import hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXPERIMENTS=('event_setclear_h0','event_setclear_h80','event_toggle_h0','event_toggle_h80')
EXPECTED=(ROOT/'tests/expected_frame.hex').read_bytes()

def run(args,cwd):
    return subprocess.run([str(x) for x in args],cwd=cwd,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True).stdout

for name in EXPERIMENTS:
    d=ROOT/'experiments'/name
    checks=[];logs=[]
    models=(('rtl',[d/'ishi_vga_core.v',d/'ishi_logo.v']),
            ('gates',[d/'out/ishi_vga_core_pnr.v',d/'build/tr1um_cells.v']))
    for model,sources in models:
        exe=d/'build'/f'{model}.vvp'
        run([ROOT/'.tools/bin/iverilog','-g2012','-s','tb_vga','-o',exe,
             ROOT/'tests/tb_vga.v',*sources],d)
        for freq,half in ((6.30,'79.365079365'),(6.45,'77.519379845')):
            dump=d/'build'/f'{model}_{freq:.2f}.hex'
            log=run([ROOT/'.tools/bin/vvp',exe,'+HALF_NS='+half,'+DUMP='+str(dump)],d)
            assert 'PASS: 315017 pixel ticks' in log and 'FAIL' not in log, (name,model,freq,log)
            assert dump.read_bytes()==EXPECTED, (name,model,freq,'byte mismatch')
            checks.append({'model':model,'mhz':freq,'ticks_checked':315017,'result':'PASS'})
            logs.append(f'{model} / {freq} MHz\n{log}')
    paths=[d/'ishi_vga_core.v',d/'ishi_logo.v',d/'config.py',
           d/'out/ishi_vga_core_pnr.v',d/'build/tr1um_cells.v',ROOT/'tests/expected_frame.hex']
    result={'variant':name,'checks':checks,'sha256':{
        str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'limitations':'Unit-delay gate simulation; no parasitic extraction or routed timing.'}
    (d/'build/verification.json').write_text(json.dumps(result,indent=2)+'\n')
    (d/'build/verification.log').write_text('\n'.join(logs))
    print(name+': RTL and final netlist PASS at 6.30/6.45 MHz; 315017 ticks each',flush=True)
