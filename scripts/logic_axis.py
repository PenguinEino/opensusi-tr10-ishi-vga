#!/usr/bin/env python3
"""Espresso minimizes only 8-input interval predicates, preserving geometry factoring."""
from pathlib import Path
import sys
P=Path(__file__).resolve().parents[1]
ns={'__file__':str(P/'scripts/logic_generate.py')}
source=(P/'scripts/logic_generate.py').read_text();exec(source[:source.index('for mode in')],ns)
from pyeda.inter import exprvars,espresso_exprs,And,Or
rects=ns['rects'];write=ns['write'];direct=ns['rgb_direct'];covers=ns['covers']
def erange(v,a,b):
 return Or(*[And(*[(v[i] if val&(1<<i) else ~v[i]) for i in range(8) if mask&(1<<i)]) for val,mask in covers(a,b)])
def vv(e):
 if e.is_zero():return "1'b0"
 if e.is_one():return "1'b1"
 s=str(e)
 if s.startswith('Or('):return '('+' | '.join(vv(a) for a in e.xs)+')'
 if s.startswith('And('):return '('+' & '.join(vv(a) for a in e.xs)+')'
 return s
for mode in ['sop','pos','mixed']:
 lines=[];labels={}
 for axis,indices in [('h',(1,3)),('y',(2,4))]:
  ivs=sorted(set((r[indices[0]],r[indices[1]]) for r in rects));v=exprvars(axis,8)
  fs=[erange(v,a,b) for a,b in ivs]
  sop=espresso_exprs(*fs);pos=espresso_exprs(*[(~f).to_dnf() for f in fs])
  for i,((a,b),sp,po) in enumerate(zip(ivs,sop,pos)):
   label=f'{axis}_range_{i}';labels[(axis,a,b)]=label
   use_pos=mode=='pos' or (mode=='mixed' and po.size<sp.size)
   lines.append(f'wire {label} = '+('~'+vv(po) if use_pos else vv(sp))+';')
 for color in [4,5,1,2,3]:
  lines.append(f'wire color_{color} = '+' | '.join(f'({labels[("h",a,c)]} & {labels[("y",b,d)]})' for co,a,b,c,d in rects if co==color)+';')
 write('axis_'+mode,lines+direct())
