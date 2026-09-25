#!/usr/bin/env python3
"""Connectivity and ownership diagnostics for a flattened-core route GDS.

Uses the pinned KLayout DB API and v59_4 LEF pin shapes. It writes diagnostics
only under experiments/routing_audit and never alters its route inputs.
"""
from pathlib import Path
from collections import defaultdict, Counter
import argparse, json, sys, math
ROOT=Path(__file__).resolve().parents[1]
APR=ROOT/'tools/APRtools/apr';sys.path.insert(0,str(APR))
import klayout.db as db
import lef_parser, rules

LAYERS={'M1':rules.M1,'M2':rules.M2,'V1':rules.V1,'GC':rules.GC,'CO':rules.CO}
class UF:
 def __init__(self):self.p={}
 def find(self,x):
  self.p.setdefault(x,x)
  if self.p[x]!=x:self.p[x]=self.find(self.p[x])
  return self.p[x]
 def union(self,a,b):
  a=self.find(a);b=self.find(b)
  if a!=b:self.p[b]=a

def box_um(box,dbu):
 return [round(box.left*dbu,4),round(box.bottom*dbu,4),round(box.right*dbu,4),round(box.top*dbu,4)]
def dbox_from_um(r,dbu):
 return db.Box(*(int(round(v/dbu)) for v in r))
def uf_region(layout,top,tag,uf):
 idx=layout.layer(*LAYERS[tag]); reg=db.Region(top.begin_shapes_rec(idx)).merged(); polys=list(reg.each())
 keys=[]
 for i,p in enumerate(polys):k=(tag,i);uf.find(k);keys.append(k)
 return reg,polys,keys
def point_component(polys,keys,pt,dbu):
 x=int(round(pt[0]/dbu));y=int(round(pt[1]/dbu));probe=db.Region(db.Box(x,y,x+1,y+1))
 hits=[]
 for p,k in zip(polys,keys):
  if p.bbox().left<=x<=p.bbox().right and p.bbox().bottom<=y<=p.bbox().top and probe.interacting(db.Region(p)).count():hits.append(k)
 return hits

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--gds',default='experiments/phys_desc5/build/postrepair_compacted.gds');ap.add_argument('--pins',default='experiments/phys_desc5/build/postrepair_pins.json');ap.add_argument('--shapes',default='experiments/phys_desc5/build/postrepair_shapes.json');ap.add_argument('--placement',default='experiments/phys_desc5/layout/placement.json');ap.add_argument('--out',default='experiments/routing_audit');ap.add_argument('--poly',action='store_true');a=ap.parse_args()
 gds=(ROOT/a.gds).resolve();pins_map=json.load(open(ROOT/a.pins));shapes_map=json.load(open(ROOT/a.shapes));place=json.load(open(ROOT/a.placement));out=(ROOT/a.out);out.mkdir(parents=True,exist_ok=True)
 lef=lef_parser.parse_lef(ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_cells.lef');ly=db.Layout();ly.read(str(gds));dbu=ly.dbu;top=ly.cell('ishi_vga_core');assert top
 foreign={v['foreign']:k for k,v in lef.items()}
 row_origins=sorted({round(i.trans.disp.y*dbu,3) for i in top.each_inst() if i.cell.name in foreign})
 assert len(row_origins)==len(place['rows']),(row_origins,len(place['rows']))
 instrefs=defaultdict(list)
 for ir in top.each_inst():
  x=round(ir.trans.disp.x*dbu,3);y=round(ir.trans.disp.y*dbu,3);instrefs[(ir.cell.name,x,y)].append(ir)
 uf=UF(); regs={}; polys={}; keys={}
 for tag in ('M1','M2','V1'):
  regs[tag],polys[tag],keys[tag]=uf_region(ly,top,tag,uf)
 # Each actual V1 cut polygon joins every M1/M2 polygon it physically intersects.
 for vi,v in enumerate(polys['V1']):
  vr=db.Region(v);hits=[]
  for tag in ('M1','M2'):
   for p,k in zip(polys[tag],keys[tag]):
    if p.bbox().overlaps(v.bbox()) and vr.interacting(db.Region(p)).count():hits.append(k)
  for k in hits:uf.union(keys['V1'][vi],k)
 if a.poly:
  regs['GC'],polys['GC'],keys['GC']=uf_region(ly,top,'GC',uf)
  regs['CO'],polys['CO'],keys['CO']=uf_region(ly,top,'CO',uf)
  # A CO joins GC to M1 only where physically overlapping. AP/AN are omitted,
  # so gate crossings over source/drain do not short them or bridge GC.
  for ci,co in enumerate(polys['CO']):
   cr=db.Region(co);hits=[]
   for tag in ('GC','M1'):
    for p,k in zip(polys[tag],keys[tag]):
     if p.bbox().overlaps(co.bbox()) and cr.interacting(db.Region(p)).count():hits.append(k)
   for k in hits:uf.union(keys['CO'][ci],k)
 # Rebuild actual pin geometry labels from GDS transforms and v59_4 LEF polygons.
 missing_instances=[];map_by_pin=defaultdict(list);actual_pin_map=defaultdict(list);missing_pin=[];pin_roots_map={};pin_boxes_map={}
 for net,pins in pins_map.items():
  for inst,pin,x,y in pins:map_by_pin[(inst,pin)].append((net,x,y))
 matched=0
 # Group actual intended labels by physical connected component.
 compnets=defaultdict(set);comppins=defaultdict(list);netroots=defaultdict(set)
 for ri,row in enumerate(place['rows']):
  y0=row_origins[ri]
  for item in row:
   typ=item['type'];inst=item['name'];refs=instrefs.get((lef[typ]['foreign'],round(item['x'],3),y0),[])
   if not refs:
    missing_instances.append({'instance':inst,'type':typ,'x_um':item['x'],'row_y_um':y0})
    continue
   if len(refs)!=1:raise RuntimeError(f'Ambiguous GDS placement for {inst}: {len(refs)} matching references')
   ir=refs[0];matched+=1
   for pn,meta in item.get('pins',{}).items():
    net=meta.get('net');use=meta.get('use')
    if not net or use in ('POWER','GROUND') or pn not in lef[typ]['pins']:continue
    rects=[];hits=[]
    for layer,x1,y1,x2,y2 in lef[typ]['pins'][pn]['rects']:
     tag={'METAL1':'M1','METAL2':'M2'}.get(layer)
     if not tag:continue
     b=db.Box(*(int(round(v/dbu)) for v in (x1,y1,x2,y2))).transformed(ir.trans);rects.append((tag,b))
     for poly,k in zip(polys[tag],keys[tag]):
      if poly.bbox().overlaps(b) and db.Region(poly).interacting(db.Region(b)).count():hits.append((tag,k))
    roots={uf.find(k) for _,k in hits}
    if not roots:
     missing_pin.append({'net':net,'instance':inst,'pin':pn,'rects':[{'layer':t,'box_um':box_um(b,dbu)} for t,b in rects]})
     continue
    pin_roots_map[(net,inst,pn)]=roots;pin_boxes_map[(net,inst,pn)]=rects
    for root in roots:
     compnets[root].add(net);comppins[root].append({'net':net,'instance':inst,'pin':pn,'rects':[{'layer':t,'box_um':box_um(b,dbu)} for t,b in rects]});netroots[net].add(root)
    # Export one actual v59_4 pin-metal center that touches this labeled component.
    chosen=None
    for t,b in rects:
     if any(uf.find(k) in roots for poly,k in zip(polys[t],keys[t]) if poly.bbox().overlaps(b) and db.Region(poly).interacting(db.Region(b)).count()):
      bb=box_um(b,dbu);chosen=[(bb[0]+bb[2])/2,(bb[1]+bb[3])/2];break
    if chosen is None:
     bb=box_um(rects[0][1],dbu);chosen=[(bb[0]+bb[2])/2,(bb[1]+bb[3])/2]
    actual_pin_map[net].append([inst,pn,round(chosen[0],4),round(chosen[1],4)])
 # Attach route-map boxes to physical components by exact center hit.
 mapped=defaultdict(list);map_unlocated=[]
 for net,items in shapes_map.items():
  for si,(tag,x0,y0,x1,y1) in enumerate(items):
   if tag not in ('M1','M2'):continue
   b=dbox_from_um((x0,y0,x1,y1),dbu);ctr=((x0+x1)/2,(y0+y1)/2);hits=point_component(polys[tag],keys[tag],ctr,dbu)
   roots={uf.find(k) for k in hits}
   if not roots:map_unlocated.append({'net':net,'index':si,'layer':tag,'box':[x0,y0,x1,y1]})
   for root in roots:mapped[root].append({'net':net,'index':si,'layer':tag,'box':[x0,y0,x1,y1]})
 shorts=[]
 for root,nets in compnets.items():
  if len(nets)<2:continue
  groups={}
  allpolys=[]
  for tag in ('M1','M2'):
   for i,(p,k) in enumerate(zip(polys[tag],keys[tag])):
    if uf.find(k)==root:allpolys.append((tag,p))
  bbox=[min(p.bbox().left for _,p in allpolys)*dbu,min(p.bbox().bottom for _,p in allpolys)*dbu,max(p.bbox().right for _,p in allpolys)*dbu,max(p.bbox().top for _,p in allpolys)*dbu]
  recs=mapped.get(root,[]);cross=[]
  # Map-record overlaps offer actionable route crossing coordinates (ownership labels from maps).
  for i,a1 in enumerate(recs):
   for b1 in recs[i+1:]:
    if a1['net']==b1['net'] or a1['layer']!=b1['layer']:continue
    A=a1['box'];B=b1['box'];ix0=max(A[0],B[0]);iy0=max(A[1],B[1]);ix1=min(A[2],B[2]);iy1=min(A[3],B[3])
    if ix0<=ix1+1e-4 and iy0<=iy1+1e-4:
     cx=(ix0+ix1)/2;cy=(iy0+iy1)/2;near=[]
     for pp in comppins[root]:
      for pr in pp['rects']:
       q=pr['box_um']
       if q[0]-2.7<=cx<=q[2]+2.7 and q[1]-2.7<=cy<=q[3]+2.7:near.append(f"{pp['instance']}.{pp['pin']}({pp['net']})")
     cross.append({'nets':[a1['net'],b1['net']],'layer':a1['layer'],'intersection_um':[round(ix0,3),round(iy0,3),round(ix1,3),round(iy1,3)],'map_indices':[a1['index'],b1['index']],'nearby_actual_cell_pins':sorted(set(near)),'candidate_local_m2_span_um':[round(cx-2.7,3),round(cy-2.7,3),round(cx+2.7,3),round(cy+2.7,3)]})
  via_locations=[];via_crossings=[]
  for v,k in zip(polys['V1'],keys['V1']):
   if uf.find(k)!=root:continue
   vb=v.bbox();via_locations.append(box_um(vb,dbu));mnet=set();nnet=set()
   for rec in recs:
    A=rec['box'];B=box_um(vb,dbu)
    if A[0]<=B[2] and A[2]>=B[0] and A[1]<=B[3] and A[3]>=B[1]:
     (mnet if rec['layer']=='M1' else nnet).add(rec['net'])
   if mnet and nnet and any(x!=y for x in mnet for y in nnet):
    cx=(vb.left+vb.right)*dbu/2;cy=(vb.bottom+vb.top)*dbu/2
    via_crossings.append({'via_box_um':box_um(vb,dbu),'m1_map_nets':sorted(mnet),'m2_map_nets':sorted(nnet),'different_nets':sorted(set(x for x in mnet for y in nnet if x!=y)),'candidate_local_m2_span_um':[round(cx-2.7,3),round(cy-2.7,3),round(cx+2.7,3),round(cy+2.7,3)]})
  cellpins=[{'net':p['net'],'instance':p['instance'],'pin':p['pin'],'rects':p['rects']} for p in comppins[root]]
  shorts.append({'component':repr(root),'nets':sorted(nets),'bbox_um':[round(v,3) for v in bbox],'pin_count':len(comppins[root]),'pins':comppins[root][:80],'unmapped_cell_pin_geometry':cellpins,'map_shape_count':len(recs),'crossings':cross[:80],'via_locations_um':via_locations,'via_crossings':via_crossings,'candidate_local_m2_span_um': [round(bbox[0]-2.7,3),round(bbox[1]-2.7,3),round(bbox[2]+2.7,3),round(bbox[3]+2.7,3)]})
 # Classify map points as actual LEF rectangles, route anchors on the pin's
 # own component, other-net metal, or no metal. Distance to center alone is not validity.
 anchor_classes=Counter();anchor_examples=[];max_anchor_distance=0.0;over15=[];inside_count=0;samecomp_count=0
 for net,entries in pins_map.items():
  for inst,pn,x,y in entries:
   key=(net,inst,pn);rects=pin_boxes_map.get(key,[]);roots=pin_roots_map.get(key,set());inside=False;best=1e99
   xi=int(round(x/dbu));yi=int(round(y/dbu))
   for tag,b in rects:
    dx=max(b.left-xi,0,xi-b.right)*dbu;dy=max(b.bottom-yi,0,yi-b.top)*dbu;best=min(best,math.hypot(dx,dy))
    if b.left<=xi<=b.right and b.bottom<=yi<=b.top:inside=True
   maproots=set()
   for tag in ('M1','M2'):
    maproots.update(uf.find(k) for k in point_component(polys[tag],keys[tag],(x,y),dbu))
   if inside:cat='inside_actual_LEF_pin_rect';inside_count+=1
   elif maproots & roots:cat='on_same_pin_component_route_anchor';samecomp_count+=1
   elif maproots:cat='on_other_metal_component'
   else:cat='no_current_metal_at_point'
   anchor_classes[cat]+=1;max_anchor_distance=max(max_anchor_distance,best)
   if best>15:over15.append({'net':net,'instance':inst,'pin':pn,'map_point_um':[x,y],'nearest_actual_LEF_rect_distance_um':round(best,3),'classification':cat})
   if cat!='inside_actual_LEF_pin_rect' and len(anchor_examples)<100:anchor_examples.append({'net':net,'instance':inst,'pin':pn,'map_point_um':[x,y],'nearest_actual_LEF_rect_distance_um':round(best,3),'classification':cat})
 # Full direct-geometry ownership inventory for all cell-owned M1/M2/V1 shapes.
 owner_counts=Counter();owner_samples=[]
 for tag in ('M1','M2','V1'):
  it=top.begin_shapes_rec(ly.layer(*LAYERS[tag]))
  while not it.at_end():
   shape=it.shape();cell=it.cell().name;owner_counts[(tag,cell)]+=1
   if cell!='ishi_vga_core' and len(owner_samples)<25000:
    bb=shape.bbox().transformed(it.trans());owner_samples.append({'layer':tag,'owner_cell':cell,'bbox_um':box_um(bb,dbu),'path':str(it.path())})
   it.next()
 report={'mode':'GC/CO modeled; AP/AN ignored' if a.poly else 'M1/M2/V1 only','input':str(gds.relative_to(ROOT)),'top':'ishi_vga_core','dbu_um':dbu,'nets_in_route_maps':len(shapes_map),'route_map_shapes':sum(len(v) for v in shapes_map.values()),'placement_instances_matched_to_actual_gds':matched,'placement_instances_missing_from_gds':missing_instances[:100],'actual_pin_shapes_labeled':sum(len(v) for v in actual_pin_map.values()),'missing_actual_pin_count':len(missing_pin),'missing_actual_pin_examples':missing_pin[:200],'actual_pin_map':dict(actual_pin_map),'placement_signal_pin_count':sum(1 for row in place['rows'] for item in row for pp in item.get('pins',{}).values() if pp.get('net') and pp.get('use') not in ('POWER','GROUND')),'unique_source_pin_map_keys':len(map_by_pin),'duplicated_source_pin_entries':sum(len(v)-1 for v in map_by_pin.values() if len(v)>1),'placement_signal_pins_missing_from_source_map':sum(1 for row in place['rows'] for item in row for pn,pp in item.get('pins',{}).items() if pp.get('net') and pp.get('use') not in ('POWER','GROUND') and not map_by_pin.get((item['name'],pn))),'open_net_count':sum(1 for n,r in netroots.items() if len(r)>1),'open_nets':{n:[repr(x) for x in roots] for n,roots in netroots.items() if len(roots)>1},'map_pin_anchor_classifications':dict(anchor_classes),'map_pin_inside_actual_lef_rect_count':inside_count,'map_pin_on_same_pin_component_count':samecomp_count,'map_pin_outside_all_actual_lef_rects_count':sum(anchor_classes.values())-inside_count,'map_pin_nearest_lef_rect_over_15um_count':len(over15),'map_pin_nearest_lef_rect_over_15um_examples':over15[:200],'map_pin_anchor_class_examples':anchor_examples,'physical_components':{tag:len(polys[tag]) for tag in (('M1','M2','V1','GC','CO') if a.poly else ('M1','M2','V1'))},'actual_short_component_count':len(shorts),'actual_short_net_pair_count':sum(len(s['nets'])*(len(s['nets'])-1)//2 for s in shorts),'mapped_direct_crossing_pair_count':len({tuple(sorted(c['nets'])) for s in shorts for c in s['crossings']}),'actual_short_components':shorts,'map_shape_unlocated_count':len(map_unlocated),'map_shape_unlocated_examples':map_unlocated[:100],'gds_owner_shape_counts':{f'{l}:{c}':n for (l,c),n in owner_counts.items()},'gds_cell_geometry_samples':owner_samples[:200]}
 (out/'metal_connectivity.json').write_text(json.dumps(report,indent=2)+'\n')
 (out/'actual_pin_map.json').write_text(json.dumps(dict(actual_pin_map),indent=2)+'\n')
 md=['# Metal connectivity audit','',f"GDS `{gds.relative_to(ROOT)}`; {matched} actual placed instances matched, {sum(len(v) for v in actual_pin_map.values())} signal pins labeled from v59_4 LEF and GDS transforms.",'',f"Actual short components: **{len(shorts)}**; transitive within-component net pairs: **{report['actual_short_net_pair_count']}**; directly overlapping routed net pairs: **{report['mapped_direct_crossing_pair_count']}**. Source map points: {dict(anchor_classes)}. Unlocated route-map shapes: {len(map_unlocated)}.",'','## Shorted components']
 for i,s in enumerate(shorts,1):
  md += ['',f"### {i}. Nets {', '.join(s['nets'])}",f"BBox {s['bbox_um']} µm; mapped crossing candidates {len(s['crossings'])}; pins {s['pin_count']}."]
  for x in s['crossings'][:12]:md.append(f"- {x['layer']} overlap {x['intersection_um']} µm; nets {x['nets']}; shape indices {x['map_indices']}; candidate local M2 {x['candidate_local_m2_span_um']} µm; nearby pins {x['nearby_actual_cell_pins']}")
  for x in s['via_crossings'][:12]:md.append(f"- V1 {x['via_box_um']} µm joins map M1 nets {x['m1_map_nets']} with M2 nets {x['m2_map_nets']}; local M2 candidate {x['candidate_local_m2_span_um']} µm")
  if not s['crossings']:md.append('- No cross-net map rectangle overlap found inside this component; inspect cell/via geometry and near-pin connectivity in JSON.')
  md.append(f"- Candidate local M2 edit window: {s['candidate_local_m2_span_um']} µm (diagnostic bbox expansion, not a repair recommendation).")
 md += ['', '## Pin-map coordinate audit','']
 for x in anchor_examples[:100]:md.append(f"- {x['net']} {x['instance']}.{x['pin']}: {x['map_point_um']} µm, nearest actual pin rect gap {x['nearest_actual_LEF_rect_distance_um']} µm, {x['classification']}")
 (out/'metal_connectivity.md').write_text('\n'.join(md)+'\n')
 print(f"instances={matched}; signal pins={report['actual_pin_shapes_labeled']}; shorts={len(shorts)} pair_count={report['actual_short_net_pair_count']} map_anchor_classes={dict(anchor_classes)} missing_pin={len(missing_pin)} open_nets={report['open_net_count']}; report={out/'metal_connectivity.md'}")
if __name__=='__main__':main()
