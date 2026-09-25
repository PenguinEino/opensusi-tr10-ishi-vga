#!/usr/bin/env python3
"""Trial orthogonal maze route around real M1/M2/cell obstacles."""
import ast
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import numpy as np
from check_toolchain import ROOT, verify
sys.path.insert(0,str(ROOT/'tools/APRtools/apr'))
import rules
import lef_parser
import klayout.db as db
from poly_core_trial import deck_limit

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def settings(design):
 for n in ast.parse((design/'config.py').read_text()).body:
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MAZE_ROUTE' for t in n.targets):return ast.literal_eval(n.value)
 raise RuntimeError('MAZE_ROUTE settings missing')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--design-root',type=Path,default=ROOT/'experiments/maze_route')
 args=ap.parse_args();design=args.design_root.resolve()
 verify();st=settings(design);out=design/'build';out.mkdir(exist_ok=True)
 source=ROOT/st['source_gds'];assert sha(source)==st['source_sha256']
 ly=db.Layout();ly.read(str(source));top=ly.cell('ishi_vga_core');dbu=ly.dbu
 def u(v):return round(v/dbu)
 shapes=json.loads((ROOT/st['shapes']).read_text());removed=[]
 for index in st['remove_shape_indices']:
  tag,*coords=shapes[st['target']][index];box=db.Box(*(u(v) for v in coords));layer=ly.layer(*getattr(rules,tag))
  matches=[s for s in top.shapes(layer).each() if s.is_box() and s.box==box]
  expected=st.get('remove_shape_multiplicity',{}).get(str(index),1)
  assert len(matches)==expected,(index,len(matches),expected)
  for s in matches:top.shapes(layer).erase(s);removed.append([tag,*coords])
 removed_vias=[]
 for x,y in st.get('remove_vias_um',[]):
  refs=[i for i in top.each_inst() if i.cell.name.startswith('via_1') and i.trans.disp==db.Vector(u(x),u(y))]
  assert refs,('missing top-level route via',x,y)
  for i in refs:removed_vias.append({'cell':i.cell.name,'trans':i.trans.to_s(),'xy_um':[x,y]});i.delete()
 tags=('M1','M2','V1','GC','GR','CO')
 reg={n:db.Region(top.begin_shapes_rec(ly.layer(*getattr(rules,n)))).merged() for n in tags}
 l2n=db.LayoutToNetlist(top.name,dbu)
 for n,r in reg.items():l2n.register(r,n);l2n.connect(r)
 for a,b in [('M1','V1'),('M2','V1'),('M1','CO'),('GC','CO')]:l2n.connect(reg[a],reg[b])
 l2n.extract_netlist()
 pins=json.loads((ROOT/st['actual_pins']).read_text())
 lef=lef_parser.parse_lef(ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_cells.lef')
 place=json.loads((ROOT/st['placement']).read_text());types={i['name']:i['type'] for row in place['rows'] for i in row}
 def pin_layer(inst,pin):
  metals={r[0] for r in lef[types[inst]]['pins'][pin]['rects'] if r[0] in ('METAL1','METAL2')}
  assert len(metals)==1,(inst,pin,metals)
  return {'METAL1':'M1','METAL2':'M2'}[next(iter(metals))]
 own=[];own_names=set()
 for inst,pin,x,y in pins[st['target']]:
  n=l2n.probe_net(reg[pin_layer(inst,pin)],db.Point(u(x),u(y)));assert n is not None
  if n.expanded_name() not in own_names:own.append(n);own_names.add(n.expanded_name())
 assert len(own)==2,f'Need exactly two disconnected target components, got {len(own)}'
 for net,pp in pins.items():
  if net==st['target']:continue
  for inst,pin,x,y in pp:
   n=l2n.probe_net(reg[pin_layer(inst,pin)],db.Point(u(x),u(y)))
   assert n is None or n.expanded_name() not in own_names,(net,inst,pin,'target component still shorted after removal')
 owned=[{tag:l2n.shapes_of_net(n,reg[tag],True).merged() for tag in ('M1','M2','V1')} for n in own]
 foreign={tag:(reg[tag]-owned[0][tag]-owned[1][tag]).merged() for tag in ('M1','M2','V1')}
 x0,y0,x1,y1=st['bounds_um'];step=st['grid_um'];w=round((x1-x0)/step)+1;h=round((y1-y0)/step)+1
 def raster(region):
  arr=np.zeros((h,w),dtype=np.uint8)
  clip=region & db.Region(db.Box(u(x0-step),u(y0-step),u(x1+step),u(y1+step)))
  for p in clip.decompose_trapezoids_to_region().each():
   b=p.bbox()
   xa=max(0,int(np.ceil((b.left*dbu-x0)/step-1e-7)));xb=min(w-1,int(np.floor((b.right*dbu-x0)/step+1e-7)))
   ya=max(0,int(np.ceil((b.bottom*dbu-y0)/step-1e-7)));yb=min(h-1,int(np.floor((b.top*dbu-y0)/step+1e-7)))
   if xa<=xb and ya<=yb:arr[ya:yb+1,xa:xb+1]=1
  return arr
 # Conservative wide-M1 clearance also covers power rails.
 widths={'M1':rules.M1_WIDTH_MIN,'M2':rules.M2_WIRE_WIDTH}
 gaps={'M1':rules.M1_WIDE_SPACE_MIN,'M2':rules.M2_SPACE_MIN}
 allow=np.stack([1-raster(foreign[n].sized(u(gaps[n]+widths[n]/2))) for n in ('M1','M2')])
 vp=rules.V1_CUT/2
 co_gap,_=deck_limit(ROOT/'tools/TR-1um/libs.tech/klayout/tech/drc/run.drc','V1.CO')
 forbidden=(foreign['M1'].sized(u(gaps['M1']+vp+rules.V1_ENC_M1))+
  foreign['M2'].sized(u(gaps['M2']+vp+rules.V1_ENC_M2))+
  (reg['GC']+reg['GR']).sized(u(vp+rules.V1_GA_SPACE_MIN))+
  reg['CO'].sized(u(vp+co_gap))+reg['V1'].sized(u(vp+rules.V1_SPACE_MIN)))
 via=1-raster(forbidden)
 terminal=[np.stack([raster(owned[k][tag]) for tag in ('M1','M2')]) & allow for k in (0,1)]
 # Smaller terminal first reduces the multi-source queue.
 if terminal[0].sum()>terminal[1].sum():terminal.reverse()
 assert terminal[0].any() and terminal[1].any(), 'No legal terminal access on search grid'
 print('Grid',w,h,'free',int(allow.sum()),'vias',int(via.sum()),'terminalnodes',[int(t.sum()) for t in terminal],flush=True)
 binary=out/'grid.bin'
 with binary.open('wb') as f:
  f.write(struct.pack('<4i',w,h,st['via_cost_steps'],st['max_expanded_nodes']))
  for a in (allow,via,*terminal):f.write(a.astype(np.uint8).tobytes())
 exe=out/'maze_grid';subprocess.run(['g++','-O3','-std=c++17',str(ROOT/'scripts/maze_grid.cpp'),'-o',str(exe)],check=True)
 run=subprocess.run([str(exe),str(binary),str(out/'path.txt')],text=True,capture_output=True)
 (out/'search.log').write_text(run.stdout+run.stderr);print(run.stderr,flush=True)
 if run.returncode:raise RuntimeError('No maze path found')
 path=[tuple(map(int,l.split())) for l in (out/'path.txt').read_text().splitlines()]
 added={n:[] for n in ('M1','M2','V1')}
 def rect(tag,xa,ya,xb,yb):
  coords=[round(v/rules.MFG_GRID)*rules.MFG_GRID for v in (xa,ya,xb,yb)]
  top.shapes(ly.layer(*getattr(rules,tag))).insert(db.Box(*(u(v) for v in coords)))
  added[tag].append([round(v,4) for v in coords])
 # Compress consecutive collinear moves, keeping each layer-change point.
 compressed=[path[0]]
 for i in range(1,len(path)-1):
  a,b,c=path[i-1:i+2]
  if (b[0]-a[0],b[1]-a[1],b[2]-a[2])!=(c[0]-b[0],c[1]-b[1],c[2]-b[2]):compressed.append(b)
 compressed.append(path[-1]);via_count=0
 for a,b in zip(compressed,compressed[1:]):
  za,ia,ja=a;zb,ib,jb=b;xa=x0+ia*step;ya=y0+ja*step;xb=x0+ib*step;yb=y0+jb*step
  if za!=zb:
   assert ia==ib and ja==jb;via_count+=1
   for tag,half in [('V1',vp),('M1',vp+rules.V1_ENC_M1),('M2',vp+rules.V1_ENC_M2)]:rect(tag,xa-half,ya-half,xa+half,ya+half)
  else:
   tag=('M1','M2')[za];hw=widths[tag]/2
   rect(tag,min(xa,xb)-hw,min(ya,yb)-hw,max(xa,xb)+hw,max(ya,yb)+hw)
 dest=out/'candidate.gds';save=db.SaveLayoutOptions();save.gds2_write_timestamps=False;ly.write(str(dest),save);assert sha(source)==st['source_sha256']
 manifest={'source_gds':st['source_gds'],'source_sha256':sha(source),'candidate_sha256':sha(dest),
  'config_sha256':sha(design/'config.py'),'generator_sha256':sha(Path(__file__)),'solver_sha256':sha(ROOT/'scripts/maze_grid.cpp'),
  'input_hashes':{p:sha(ROOT/p) for p in [st['shapes'],st['actual_pins'],st['placement'],'toolchain.lock.json','tools/APRtools/apr/rules.py','tools/TR-1um/libs.tech/klayout/tech/drc/run.drc']},
  'grid_sha256':sha(binary),'path_sha256':sha(out/'path.txt'),
  'removed_boxes':removed,'removed_vias':removed_vias,'added_boxes':added,'path_nodes':len(path),'vias':via_count,
  'bbox_um':[top.dbbox().left,top.dbbox().bottom,top.dbbox().right,top.dbbox().top],
  'status':'TRIAL ONLY; full actual-pin connectivity and official DRC not yet run'}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('Candidate',dest,'vias',via_count,flush=True)
if __name__=='__main__':main()
