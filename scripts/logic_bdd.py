#!/usr/bin/env python3
"""Exact B logo as shared reduced binary decision diagrams, several orders."""
from pathlib import Path
import json,sys
P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P/'scripts'))
# Import common writer without re-running existing generator.
source=(P/'scripts/logic_generate.py').read_text();ns={ '__file__':str(P/'scripts/logic_generate.py') }
exec(source[:source.index('for mode in')],ns)
write=ns['write'];rects=ns['rects'];pal=ns['pal']
pixels=[[63]*256 for _ in range(256)]
for co,a,b,c,d in rects:
 for yy in range(b,d):pixels[yy][a:c]=[pal[co]]*(c-a)
orders={
 'xy_msb':list(range(15,-1,-1)),
 'yx_msb':list(range(7,-1,-1))+list(range(15,7,-1)),
 'interleaved_msb':[z for i in range(7,-1,-1) for z in (i+8,i)],
 'xy_lsb':list(range(8,16))+list(range(8)),
 'interleaved_lsb':[z for i in range(8) for z in (i+8,i)],
}
for name,order in orders.items():
 nodes={};sequence=[];cache={}
 def node(depth,values):
  if not any(values):return 0
  if all(values):return 1
  key=(depth,values)
  if key in cache:return cache[key]
  n=len(values)//2;lo=node(depth+1,values[:n]);hi=node(depth+1,values[n:])
  if lo==hi:result=lo
  else:
   nk=(order[depth],lo,hi)
   if nk not in nodes:nodes[nk]=len(nodes)+2;sequence.append(nk)
   result=nodes[nk]
  cache[key]=result
  return result
 table=[]
 for k in range(65536):
  coord=sum(((k>>(15-i))&1)<<b for i,b in enumerate(order))
  table.append(pixels[coord&255][coord>>8])
 outputs=[node(0,bytes((v>>bit)&1 for v in table)) for bit in range(6)]
 def ref(idx):return ("1'b"+str(idx)) if idx<2 else f'n{idx}'
 lines=[]
 for (bit,lo,hi),idx in nodes.items():
  v=f'h[{bit-8}]' if bit>=8 else f'y[{bit}]'
  lines.append(f'wire n{idx} = {v} ? {ref(hi)} : {ref(lo)};')
 for i,idx in enumerate(outputs):lines.append(f'assign rgb[{i}] = {ref(idx)};')
 write('bdd_'+name,lines)
 print(name,'nodes',len(nodes),flush=True)
