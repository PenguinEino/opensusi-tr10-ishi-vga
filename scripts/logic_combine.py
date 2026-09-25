#!/usr/bin/env python3
"""Combine exact geometry factoring with architecture team's offset counters."""
from pathlib import Path
import json,sys,re
P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P/'.tools/logic_pyeda'))
from pyeda.inter import exprvars,And,Or,espresso_exprs
ns={'__file__':str(P/'scripts/logic_generate.py')}
src=(P/'scripts/logic_generate.py').read_text();exec(src[:src.index('for mode in')],ns)
write=ns['write'];rects=ns['rects'];covers=ns['covers'];masked=ns['masked']
def ranges(a,b,off):
 a=(a+off)%256;b=(b+off)%256
 return [(a,b)] if a<b else ([(a,256),(0,b)] if b else [(a,256)])
def mask(axis,a,b,off):return '('+' | '.join(masked(axis,lo,hi) for lo,hi in ranges(a,b,off))+')'
def erange(v,a,b,off):
 return Or(*[And(*[(v[i] if val&(1<<i) else ~v[i]) for i in range(8) if m&(1<<i)]) for lo,hi in ranges(a,b,off) for val,m in covers(lo,hi)])
def vv(e):
 if e.is_zero():return "1'b0"
 if e.is_one():return "1'b1"
 s=str(e)
 if s.startswith('Or('):return '('+' | '.join(vv(a) for a in e.xs)+')'
 if s.startswith('And('):return '('+' & '.join(vv(a) for a in e.xs)+')'
 return s
for ho,vo in [(-48,0),(-56,0)]:
 arch=P/'experiments'/f'arch_offset_h{ho}'.replace('-','m')
 for mode in ['masked','pos','sop']:
  lines=[];labels={}
  if mode!='masked':
   for axis,inds,off in [('h',(1,3),ho),('y',(2,4),vo//4)]:
    ivs=sorted(set((r[inds[0]],r[inds[1]]) for r in rects));v=exprvars(axis,8)
    fs=[erange(v,a,b,off) for a,b in ivs]
    if mode=='pos':
     fs=[erange(v,b,a,off) for a,b in ivs]
    fs=espresso_exprs(*fs)
    for i,((a,b),f) in enumerate(zip(ivs,fs)):
     label=f'{axis}_range_{i}';labels[(axis,a,b)]=label
     lines.append(f'wire {label} = '+('~' if mode=='pos' else '')+vv(f)+';')
  for color in [4,5,1,2,3]:
   terms=[]
   for co,a,b,c,d in rects:
    if co!=color:continue
    x=labels[('h',a,c)] if labels else mask('h',a,c,ho)
    y=labels[('y',b,d)] if labels else mask('y',b,d,vo//4)
    terms.append(f'({x} & {y})')
   lines.append(f'wire color_{color} = '+ ' | '.join(terms)+';')
  suffix=f'combo_h{ho}_{mode}'.replace('-','m');write(suffix,lines+ns['rgb_direct']())
  base=P/'experiments'/('logic_'+suffix)
  (base/'ishi_vga_core.v').write_text((arch/'ishi_vga_core.v').read_text())
  cfg=(base/'config.py').read_text().replace("str(PROJECT/'rtl/ishi_vga_core.v')",f"str(PROJECT/'experiments/logic_{suffix}/ishi_vga_core.v')")
  (base/'config.py').write_text(cfg)
  (base/'offset.json').write_text(json.dumps({'h':ho,'y':vo//4})+'\n')
