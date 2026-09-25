#!/usr/bin/env python3
"""Full external VGA equivalence of architecture candidates at both clocks."""
import sys,subprocess,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(args,cwd):
 p=subprocess.run([str(x) for x in args],cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
 return p.stdout
for name in sys.argv[1:]:
 d=ROOT/'experiments'/name
 logs=[];checks=[]
 for model,sources in [('rtl',[d/'ishi_vga_core.v',d/'ishi_logo.v']),('gates',[d/'out/ishi_vga_core_pnr.v',d/'build/tr1um_cells.v'])]:
  exe=d/'build'/f'{model}.vvp'
  run([ROOT/'.tools/bin/iverilog','-g2012','-s','tb_vga','-o',exe,ROOT/'tests/tb_vga.v',*sources],d)
  for freq,half in [(6.3,'79.365079365'),(6.45,'77.519379845')]:
   dump=d/'build'/f'{model}_{freq}.hex'
   log=run([ROOT/'.tools/bin/vvp',exe,'+HALF_NS='+half,'+DUMP='+str(dump)],d)
   assert 'PASS: 315017 pixel ticks' in log and 'FAIL' not in log
   assert dump.read_bytes()==(ROOT/'tests/expected_frame.hex').read_bytes()
   logs.append(f'{model} / {freq} MHz\n'+log)
   checks.append({'model':model,'mhz':freq,'ticks_checked':315017,'result':'PASS'})
 paths=[d/'ishi_vga_core.v',d/'ishi_logo.v',d/'config.py',d/'out/ishi_vga_core_pnr.v',ROOT/'tests/expected_frame.hex']
 result={'variant':name,'checks':checks,'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'limitations':'Unit-delay gate simulation; no parasitic extraction or routed timing.'}
 (d/'build/verification.json').write_text(json.dumps(result,indent=2)+'\n')
 (d/'build/verification.log').write_text('\n'.join(logs))
 print(name+'\n'+'\n'.join(logs),flush=True)
