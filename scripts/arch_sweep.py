#!/usr/bin/env python3
"""Run pinned upstream synthesis for generated isolated architecture variants."""
from pathlib import Path
import subprocess,sys,re,json
ROOT=Path(__file__).resolve().parents[1]
results=[]
for name in sys.argv[1:]:
 d=ROOT/'experiments'/name
 log=d/'build/synthesis.log'
 with log.open('w') as f:
  proc=subprocess.run([sys.executable,ROOT/'scripts/run_apr.py','--design-root',str(d.relative_to(ROOT)),'syn/syn.sh'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 s=log.read_text();m=re.findall(r'ishi_vga_core\s+(\d+) セル.*?([\d,]+) um2',s)
 result={'name':name,'synthesis_exit':proc.returncode,'cells':int(m[-1][0]) if m else None,'area':int(m[-1][1].replace(',','')) if m else None}
 results.append(result)
 print(json.dumps(result),flush=True)
(ROOT/'experiments/arch_base/build/sweep_latest.json').write_text(json.dumps(results,indent=2)+'\n')
