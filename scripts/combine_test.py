#!/usr/bin/env python3
"""Verify isolated combine_* candidates in serial APR runs."""
from pathlib import Path
import sys,json,subprocess,re,hashlib
P=Path(__file__).resolve().parents[1]
failures=[]
def run(args,cwd=P,log=None):
 p=subprocess.run([str(x) for x in args],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 if log:log.write_text(p.stdout)
 if p.returncode:raise RuntimeError(p.stdout[-3500:])
 return p.stdout
for name in sys.argv[1:]:
 assert name.startswith('combine_') and '/' not in name
 b=P/'experiments'/name;build=b/'build';off=json.loads((b/'offset.json').read_text())
 try:
  ref=(P/'rtl/ishi_logo.v').read_text().replace('module ishi_logo(', 'module ishi_logo_reference_raw(')
  ref+=f"\nmodule ishi_logo_reference(input wire [7:0] h,y, output wire [5:0] rgb); wire [7:0] hh=h-8'd{off['h']%256}; wire [7:0] yy=y-8'd{off['y']%256}; ishi_logo_reference_raw r(.h(hh),.y(yy),.rgb(rgb)); endmodule\n"
  (build/'reference.v').write_text(ref)
  run([P/'.tools/bin/iverilog','-g2012','-s','tb_logo_equivalence','-o',build/'equivalence.vvp',P/'tests/tb_logo_equivalence.v',build/'reference.v',b/'ishi_logo.v'])
  out=run([P/'.tools/bin/vvp',build/'equivalence.vvp'],log=build/'equivalence.log')
  assert 'PASS: all 65536' in out and 'FAIL' not in out
  print(name,'coordinates PASS',flush=True)
  run(['python3',P/'scripts/check_toolchain.py'])
  try: out=run(['python3',P/'scripts/run_apr.py','--design-root',b,'syn/syn.sh'],log=build/'synthesis.log')
  except RuntimeError as e:
   stat=(b/'out/SYN_RESULTS.txt').read_text() if (b/'out/SYN_RESULTS.txt').exists() else ''
   if '既に BUFTH が入っている' not in stat:
    raise
   m=re.search(r'(\d+) セル.*?([\d,]+) um2',stat)
   result={'variant':name,'offset':off,'coordinates':65536,'synthesis_state':'blocked before final PNR','raw_or_merged_cells':int(m[1]) if m else None,'raw_or_merged_area_um2':int(m[2].replace(',','')) if m else None,'reason':'unmodified insert_bufth.py rejected pre-existing internal BUFTH','limits':'partial synthesis only; no final PNR/STA'}
   (build/'metrics.json').write_text(json.dumps(result,indent=2)+'\n')
   print(name,'BLOCKED at final PNR:',str(e).splitlines()[-1],flush=True);continue
  stat=(b/'out/SYN_RESULTS.txt').read_text();cells,area=re.findall(r'ishi_vga_core\s+(\d+) セル.*?([\d,]+) um2',stat)[-1]
  checks=[];outputs=out;core=b/'ishi_vga_core.v'
  for model,src in [('rtl',[core,b/'ishi_logo.v']),('gates',[b/'out/ishi_vga_core_pnr.v',build/'tr1um_cells.v'])]:
   exe=build/f'{model}.vvp';run([P/'.tools/bin/iverilog','-g2012','-s','tb_vga','-o',exe,P/'tests/tb_vga.v',*src])
   for freq,half in [(6.30,'79.365079365'),(6.45,'77.519379845')]:
    dump=build/f'{model}_{freq}.hex';o=run([P/'.tools/bin/vvp',exe,'+HALF_NS='+half,'+DUMP='+str(dump)],cwd=b)
    assert 'PASS: 315017 pixel ticks' in o and 'FAIL' not in o and dump.read_bytes()==(P/'tests/expected_frame.hex').read_bytes()
    outputs+=o;checks.append({'model':model,'mhz':freq,'result':'PASS'})
  (build/'verification.log').write_text(outputs)
  result={'variant':name,'offset':off,'cells':int(cells),'area_um2':int(area.replace(',','')),'coordinates':65536,'checks':checks,'sha256':{str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [b/'ishi_logo.v',core,b/'out/ishi_vga_core_pnr.v',b/'config.py',P/'tests/expected_frame.hex',P/'tests/tb_vga.v',P/'rtl/ishi_logo.v']},'limits':'Pre-route STA only; no parasitics, DRC, LVS.'}
  (build/'metrics.json').write_text(json.dumps(result,indent=2)+'\n');print(name,cells,area,flush=True)
 except Exception as e:
  print(name,'FAILED:',e,flush=True)
  failures.append(name)
if failures:
 raise SystemExit('Failed candidates: '+', '.join(failures))
