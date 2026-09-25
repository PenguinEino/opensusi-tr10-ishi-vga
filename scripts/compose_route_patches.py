#!/usr/bin/env python3
"""Replay independent, manifest-bound route edits onto one frozen top-cell GDS."""
from __future__ import annotations
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import klayout.db as db
from check_toolchain import ROOT, verify
sys.path.insert(0, str(ROOT / 'tools/APRtools/apr'))
import rules

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def literal_config(path: Path):
    tree=ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MAZE_ROUTE' for t in node.targets):
            cfg=ast.literal_eval(node.value)
            if not isinstance(cfg,dict):raise ValueError('MAZE_ROUTE must be a literal dict')
            return cfg
    raise ValueError(f'MAZE_ROUTE not found in {path}')

def coord_box(layout,coords):
    vals=[round(float(v)/layout.dbu) for v in coords]
    return db.Box(*vals)

def top_raw_boxes(layout,top,layer):
    li=layout.layer(*getattr(rules,layer))
    return Counter((s.box.left,s.box.bottom,s.box.right,s.box.top)
                   for s in top.shapes(li).each() if s.is_box())

def top_instances(top):
    return Counter((i.cell.name,i.trans.to_s()) for i in top.each_inst())

def cell_inventory(layout,cell):
    shapes=[]
    for li in range(layout.layers()):
        info=layout.get_info(li)
        shapes.extend((info.layer,info.datatype,s.to_s()) for s in cell.shapes(li).each())
    instances=sorted((i.cell.name,i.trans.to_s(),i.na,i.nb,i.a.x,i.a.y,i.b.x,i.b.y) for i in cell.each_inst())
    return Counter(shapes),instances

def expected_boxes(rows,layer,dbu):
    return Counter(tuple(round(float(v)/dbu) for v in row[1:]) for row in rows if row[0]==layer)

def expected_add(rows,layer,dbu):
    return Counter(tuple(round(float(v)/dbu) for v in coords) for coords in rows.get(layer,[]))

def audit_patch(patch, manifest, base_dbu):
    psource=ROOT/manifest['source_gds'];pcandidate=ROOT/patch['candidate_gds']
    if sha(psource)!=manifest['source_sha256']:raise ValueError(f"{patch['name']}: source GDS hash mismatch")
    if sha(pcandidate)!=patch['candidate_sha256'] or sha(pcandidate)!=manifest['candidate_sha256']:
        raise ValueError(f"{patch['name']}: patch candidate hash mismatch")
    if sha(ROOT/patch['manifest'])!=patch['manifest_sha256']:
        raise ValueError(f"{patch['name']}: patch manifest hash mismatch")
    a=db.Layout();a.read(str(psource));at=a.cell(manifest.get('top','ishi_vga_core'))
    b=db.Layout();b.read(str(pcandidate));bt=b.cell(manifest.get('top','ishi_vga_core'))
    if at is None or bt is None or a.dbu!=b.dbu or a.dbu!=base_dbu or at.dbbox()!=bt.dbbox():
        raise ValueError(f"{patch['name']}: patch layouts/top/bbox inconsistent")
    if {(i.layer,i.datatype) for i in a.layer_infos()}!={(i.layer,i.datatype) for i in b.layer_infos()}:
        raise ValueError(f"{patch['name']}: layer table changed")
    details=[]
    for layer in ('M1','M2','V1'):
        before=top_raw_boxes(a,at,layer);after=top_raw_boxes(b,bt,layer)
        er=expected_boxes(manifest['removed_boxes'],layer,a.dbu)
        ea=expected_add(manifest['added_boxes'],layer,a.dbu)
        if before-after!=er or after-before!=ea:
            raise ValueError(f"{patch['name']}: {layer} source→candidate raw box delta disagrees with manifest")
        details.append({'layer':layer,'removed_boxes':sum(er.values()),'added_boxes':sum(ea.values())})
    ai,bi=top_instances(at),top_instances(bt)
    expected=Counter((v['cell'],v['trans']) for v in manifest.get('removed_vias',[]))
    if ai-bi!=expected or bi-ai:
        raise ValueError(f"{patch['name']}: instance delta differs from listed route vias")
    route_layers={tuple(getattr(rules,n)) for n in ('M1','M2','V1')}
    for li in range(a.layers()):
        info=a.get_info(li);key=(info.layer,info.datatype)
        if key in route_layers:
            nonbox_a=Counter(s.to_s() for s in at.shapes(li).each() if not s.is_box())
            nonbox_b=Counter(s.to_s() for s in bt.shapes(b.layer(info.layer,info.datatype)).each() if not s.is_box())
            if nonbox_a!=nonbox_b:raise ValueError(f"{patch['name']}: non-box top geometry changed on {key}")
        else:
            all_a=Counter(s.to_s() for s in at.shapes(li).each())
            all_b=Counter(s.to_s() for s in bt.shapes(b.layer(info.layer,info.datatype)).each())
            if all_a!=all_b:raise ValueError(f"{patch['name']}: unexpected top geometry changed on {key}")
    for c in a.each_cell():
        if c.name==at.name:continue
        other=b.cell(c.name)
        if other is None or cell_inventory(a,c)!=cell_inventory(b,other):
            raise ValueError(f"{patch['name']}: nested cell geometry/hierarchy changed in {c.name}")
    return {'name':patch['name'],'manifest_path':patch['manifest'],'manifest_sha256':patch['manifest_sha256'],
            'candidate_gds':patch['candidate_gds'],'candidate_sha256':patch['candidate_sha256'],
            'source_gds':manifest['source_gds'],'source_sha256':manifest['source_sha256'],
            'generator_sha256':manifest.get('generator_sha256'),
            'config_sha256':manifest.get('config_sha256'),'geometry_delta':details,
            'removed_vias':[dict(v) for v in manifest.get('removed_vias',[])],
            'removed_boxes':manifest['removed_boxes'],'added_boxes':manifest['added_boxes']}

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--design-root',type=Path,required=True)
    args=ap.parse_args();design=(ROOT/args.design_root).resolve()
    if not design.is_relative_to(ROOT):raise ValueError('design root must be inside workspace')
    verify();cfg=literal_config(design/'config.py');build=design/'build';build.mkdir(parents=True,exist_ok=True)
    required=('source_gds','source_sha256','patches','shapes','actual_pins','placement','drawing_baseline','mask_baseline')
    missing=[k for k in required if k not in cfg]
    if missing:raise ValueError(f'missing required config fields: {missing}')
    source=ROOT/cfg['source_gds']
    if sha(source)!=cfg['source_sha256']:raise ValueError('frozen base GDS hash mismatch')
    ly=db.Layout();ly.read(str(source));top=ly.cell(cfg.get('top','ishi_vga_core'))
    if top is None:raise ValueError('base GDS lacks configured top cell')
    base_ly=db.Layout();base_ly.read(str(source));base_top=base_ly.cell(cfg.get('top','ishi_vga_core'))
    patch_records=[]
    # Preflight every provenance record and its original source→candidate edit.
    for patch in cfg['patches']:
        manifest_path=ROOT/patch['manifest'];manifest=json.loads(manifest_path.read_text())
        patch_records.append(audit_patch(patch,manifest,ly.dbu))
    operations=[]
    for patch in cfg['patches']:
        manifest=json.loads((ROOT/patch['manifest']).read_text())
        operations.append((patch['name'],manifest))
    applied=[]
    combined_removed=[];combined_added=[];combined_vias=[]
    for name,manifest in operations:
        # Validate the entire delete set before mutating this candidate.
        remove_by_layer={layer:expected_boxes(manifest['removed_boxes'],layer,ly.dbu) for layer in ('M1','M2','V1')}
        selected=[]
        for boxrows in manifest['removed_boxes']:
            combined_removed.append({'patch':name,'layer':boxrows[0],'box_um':[round(float(v),4) for v in boxrows[1:]]})
        for layer,need in remove_by_layer.items():
            li=ly.layer(*getattr(rules,layer));available=Counter((s.box.left,s.box.bottom,s.box.right,s.box.top)
                for s in top.shapes(li).each() if s.is_box())
            if available & need != need:raise ValueError(f'{name}: missing/inexact source boxes on {layer}: {need-available}')
            for box,count in need.items():
                for _ in range(count):
                    matches=[s for s in top.shapes(li).each() if s.is_box() and (s.box.left,s.box.bottom,s.box.right,s.box.top)==box]
                    if not matches:raise ValueError(f'{name}: exact route box absent on {layer}: {box}')
                    selected.append((li,matches[0]))
        via_refs=[]
        for via in manifest.get('removed_vias',[]):
            combined_vias.append({'patch':name,**via})
            matches=[i for i in top.each_inst() if i.cell.name==via['cell'] and i.trans.to_s()==via['trans']]
            if len(matches)!=1:raise ValueError(f"{name}: expected one exact via {via['cell']} {via['trans']}, found {len(matches)}")
            via_refs.append(matches[0])
        for li,shape in selected:top.shapes(li).erase(shape)
        for inst in via_refs:inst.delete()
        for layer in ('M1','M2','V1'):
            li=ly.layer(*getattr(rules,layer))
            for coords in manifest['added_boxes'].get(layer,[]):
                top.shapes(li).insert(coord_box(ly,coords))
                combined_added.append({'patch':name,'layer':layer,'box_um':[round(float(v),4) for v in coords]})
        applied.append({'name':name,'removed_box_count':sum(map(sum,(c.values() for c in remove_by_layer.values()))),
                        'removed_via_count':len(via_refs),'added_box_count':sum(len(v) for v in manifest['added_boxes'].values())})
    route_layers={tuple(getattr(rules,n)) for n in ('M1','M2','V1')}
    if {(i.layer,i.datatype) for i in base_ly.layer_infos()}!={(i.layer,i.datatype) for i in ly.layer_infos()}:
        raise ValueError('composed layer table changed')
    for layer in ('M1','M2','V1'):
        before=top_raw_boxes(base_ly,base_top,layer);after=top_raw_boxes(ly,top,layer)
        want_removed=Counter(tuple(round(float(v)/ly.dbu) for v in row['box_um']) for row in combined_removed if row['layer']==layer)
        want_added=Counter(tuple(round(float(v)/ly.dbu) for v in row['box_um']) for row in combined_added if row['layer']==layer)
        if before-after!=want_removed or after-before!=want_added:
            raise ValueError(f'composed {layer} geometry delta differs from patch operations')
    if top_instances(base_top)-top_instances(top)!=Counter((v['cell'],v['trans']) for v in combined_vias) or top_instances(top)-top_instances(base_top):
        raise ValueError('composed top-level instance delta differs from patch via operations')
    for li in range(base_ly.layers()):
        info=base_ly.get_info(li);key=(info.layer,info.datatype)
        if key in route_layers:continue
        before=Counter(s.to_s() for s in base_top.shapes(li).each())
        after=Counter(s.to_s() for s in top.shapes(ly.layer(info.layer,info.datatype)).each())
        if before!=after:raise ValueError(f'composed non-route top geometry changed on {key}')
    for c in base_ly.each_cell():
        if c.name==base_top.name:continue
        other=ly.cell(c.name)
        if other is None or cell_inventory(base_ly,c)!=cell_inventory(ly,other):
            raise ValueError(f'composed nested cell geometry/hierarchy changed in {c.name}')
    out=build/'candidate.gds'
    opts=db.SaveLayoutOptions();opts.gds2_write_timestamps=False
    ly.write(str(out),opts)
    if sha(source)!=cfg['source_sha256']:raise ValueError('base GDS changed during composition')
    result={'status':'COMPOSED; see build/verification.json for full pin, rail and official DRC checks','top':cfg.get('top','ishi_vga_core'),
      'source_gds':cfg['source_gds'],'source_sha256':sha(source),'candidate_gds':'experiments/'+str(design.relative_to(ROOT))+'/build/candidate.gds',
      'candidate_sha256':sha(out),'config_sha256':sha(design/'config.py'),'composer_sha256':sha(Path(__file__)),
      'patches':patch_records,'applied_operations':applied,
      'combined_removed_boxes':combined_removed,'combined_added_boxes':combined_added,'combined_removed_vias':combined_vias,
      'input_hashes':{k:sha(ROOT/cfg[k]) for k in ('shapes','actual_pins','placement')},
      'toolchain_lock_sha256':sha(ROOT/'toolchain.lock.json'),'pinned_rules_sha256':sha(ROOT/'tools/APRtools/apr/rules.py'),
      'drawing_baseline_sha256':sha(ROOT/cfg['drawing_baseline']),'mask_baseline_sha256':sha(ROOT/cfg['mask_baseline']),
      'pinned_drc_deck_sha256':sha(ROOT/'tools/TR-1um/libs.tech/klayout/tech/drc/run.drc'),
      'bbox_um':[top.dbbox().left,top.dbbox().bottom,top.dbbox().right,top.dbbox().top],
      'limitations':'Only top-level M1/M2/V1 boxes and exact listed top-level vias were replayed. No flattening or nested-cell edits.'}
    (build/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'candidate':str(out.relative_to(ROOT)),'sha256':result['candidate_sha256'],'patches':[p['name'] for p in cfg['patches']]},indent=2))
if __name__=='__main__':main()
