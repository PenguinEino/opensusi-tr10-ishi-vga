#!/usr/bin/env python3
"""Isolated exact-logo variants: provenance, equivalence, current upstream synth."""
from pathlib import Path
import subprocess,sys,json,re,hashlib
P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P/'scripts'))
from check_toolchain import verify
verify()
def run(args,cwd=P,log=None):
 q=subprocess.run([str(x) for x in args],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 if log:log.write_text(q.stdout)
 if q.returncode:raise RuntimeError(q.stdout[-4000:])
 return q.stdout
names=sys.argv[1:] or ['logic_direct_bounds','logic_direct_masked','logic_espresso_colors','logic_espresso_rgb','logic_factor_x','logic_factor_y']
for name in names:
 assert name.startswith('logic_') and '/' not in name
 b=P/'experiments'/name;build=b/'build'
 reference=(P/'rtl/ishi_logo.v').read_text().replace('module ishi_logo(', 'module ishi_logo_reference(')
 if (b/'offset.json').exists():
  off=json.loads((b/'offset.json').read_text())
  reference=reference.replace('module ishi_logo_reference(', 'module ishi_logo_reference_raw(')
  reference+=f'\nmodule ishi_logo_reference(input wire [7:0] h,y, output wire [5:0] rgb); wire [7:0] hh=h-8\'d{off["h"]%256}; wire [7:0] yy=y-8\'d{off["y"]%256}; ishi_logo_reference_raw r(.h(hh),.y(yy),.rgb(rgb)); endmodule\n'
 (build/'reference.v').write_text(reference)
 run([P/'.tools/bin/iverilog','-g2012','-s','tb_logo_equivalence','-o',build/'equivalence.vvp',P/'tests/tb_logo_equivalence.v',build/'reference.v',b/'ishi_logo.v'])
 out=run([P/'.tools/bin/vvp',build/'equivalence.vvp'],log=build/'equivalence.log')
 assert 'PASS: all 65536' in out and 'FAIL' not in out
 print(name,'equivalent',flush=True)
 out=run(['python3',P/'scripts/run_apr.py','--design-root',b,'syn/syn.sh'],log=build/'synthesis.log')
 assert 'FAIL' not in out
 stat=(b/'out/SYN_RESULTS.txt').read_text()
 cells,area=re.findall(r'ishi_vga_core\s+(\d+) セル.*?([\d,]+) um2',stat)[-1]
 outlog=out
 checks=[]
 core=b/'ishi_vga_core.v' if (b/'ishi_vga_core.v').exists() else P/'rtl/ishi_vga_core.v'
 for model,src in [('rtl',[core,b/'ishi_logo.v']),('gates',[b/'out/ishi_vga_core_pnr.v',build/'tr1um_cells.v'])]:
  exe=build/f'{model}.vvp'
  run([P/'.tools/bin/iverilog','-g2012','-s','tb_vga','-o',exe,P/'tests/tb_vga.v',*src])
  for freq,half in [(6.3,'79.365079365'),(6.45,'77.519379845')]:
   dump=build/f'{model}_{freq}.hex'
   o=run([P/'.tools/bin/vvp',exe,'+HALF_NS='+half,'+DUMP='+str(dump)],cwd=b)
   assert 'PASS: 315017 pixel ticks' in o and 'FAIL' not in o
   assert dump.read_bytes()==(P/'tests/expected_frame.hex').read_bytes()
   outlog+=o;checks.append({'model':model,'mhz':freq,'result':'PASS'})
 (build/'verification.log').write_text(outlog)
 result={'variant':name,'cells':int(cells),'area_um2':int(area.replace(',','')),'equivalence_coordinates':65536,'checks':checks,
 'sha256':{str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [b/'ishi_logo.v',b/'out/ishi_vga_core_pnr.v',b/'config.py',P/'config.py',core]},'limits':'Pre-route STA only; no parasitics, DRC, LVS.'}
 (build/'metrics.json').write_text(json.dumps(result,indent=2)+'\n')
 print(name,cells,area,flush=True)
