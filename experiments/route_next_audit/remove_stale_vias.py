#!/usr/bin/env python3
"""Remove only the two confirmed stale routing via instances from a copy."""
import hashlib,json,runpy
from pathlib import Path
import klayout.db as db
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def signature(path,topname):
 ly=db.Layout();ly.read(str(path));top=ly.cell(topname);res=[]
 for i in top.each_inst():
  t=i.trans;a=i.a;b=i.b
  res.append((i.cell.name,t.rot,t.is_mirror(),t.disp.x,t.disp.y,a.x,a.y,b.x,b.y,i.na,i.nb))
 return ly,top,res

def main():
 s=runpy.run_path(str(HERE/'config.py'))['SETTINGS']
 source=ROOT/s['source_gds'];dest=HERE/'build/candidate_no_stale_vias.gds'
 source_hash=sha(source)
 if source_hash!=s['source_sha256']:raise RuntimeError(f'input checkpoint hash mismatch: {source_hash}')
 ly,top,initial=signature(source,s['top']);dbu=ly.dbu
 before_bbox=top.dbbox()
 removed=[]
 for spec in s['remove_vias']:
  hits=[]
  for i in list(top.each_inst()):
   x=i.trans.disp.x*dbu;y=i.trans.disp.y*dbu
   if i.cell.name==spec['cell'] and abs(x-spec['x_um'])<dbu/2 and abs(y-spec['y_um'])<dbu/2:
    hits.append(i)
  if len(hits)!=1:raise RuntimeError(f"expected one {spec['cell']} at ({spec['x_um']},{spec['y_um']}), found {len(hits)}")
  inst=hits[0]
  removed.append({'cell':inst.cell.name,'x_um':round(inst.trans.disp.x*dbu,4),
                  'y_um':round(inst.trans.disp.y*dbu,4),'cause':spec['cause']})
  inst.delete()
 ly.write(str(dest))
 if sha(source)!=source_hash:raise RuntimeError('source GDS changed')
 outly,outtop,final=signature(dest,s['top'])
 if outtop.dbbox()!=before_bbox:raise RuntimeError('top-cell bbox changed')
 expected=list(initial)
 for r in removed:
  target=(r['cell'],0,False,round(r['x_um']/dbu),round(r['y_um']/dbu),0,0,0,0,0,0)
  expected.remove(target)
 if sorted(final)!=sorted(expected):raise RuntimeError('unexpected instance changes beyond the two requested vias')
 result={'status':'generated; connectivity/DRC pending','input_gds':s['source_gds'],
  'input_sha256':source_hash,'output_gds':str(dest.relative_to(ROOT)),
  'output_sha256':sha(dest),'reference_layout_gds':s['reference_layout_gds'],
  'pins':s['pins'],'pins_sha256':sha(ROOT/s['pins']),'shapes':s['shapes'],
  'shapes_sha256':sha(ROOT/s['shapes']),'placement':s['placement'],
  'placement_sha256':sha(ROOT/s['placement']),'config_sha256':sha(HERE/'config.py'),
  'script_sha256':sha(Path(__file__)),'removed_refs':removed,'all_other_instance_refs_unchanged':True,
  'bbox_um':[before_bbox.left,before_bbox.bottom,before_bbox.right,before_bbox.top],
  'limitations':'Only exact stale via_1$2 refs were removed; this checkpoint remains experimental until full geometry audit and official DRC.'}
 (HERE/'build/removal_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
