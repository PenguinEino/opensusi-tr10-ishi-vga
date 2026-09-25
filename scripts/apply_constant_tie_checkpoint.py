#!/usr/bin/env python3
"""Apply the reviewed constant-high tie patch to a same-placement checkpoint."""
import hashlib, json, os, runpy, sys, collections
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_toolchain import verify

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    verify()
    design=ROOT/'experiments/routed_checkpoint'
    sys.path[:0]=[str(design),str(ROOT/'tools/APRtools/apr')]
    cfg=runpy.run_path(str(design/'config.py'))
    st=cfg['CONSTANT_TIE_INTEGRATION']; build=design/'build';build.mkdir(parents=True,exist_ok=True)
    os.environ['APRTOOLS']=str(ROOT/'tools/APRtools');os.environ['TR1UM_PDK']=str(ROOT/'tools/TR-1um')
    sys.path.insert(0,str(ROOT/'tools/APRtools/apr'))
    import klayout.db as db
    import rules,lef_parser
    source=ROOT/st['source_gds'];reference=ROOT/st['reference_gds'];patch_path=ROOT/st['patch_json']
    pins_path=ROOT/st['actual_pins'];placement_path=ROOT/st['placement']
    shapes_path=ROOT/st['routing_shapes'];source_sha=sha(source);reference_sha=sha(reference)
    patch_sha=sha(patch_path);pin_sha=sha(pins_path);shape_sha=sha(shapes_path)
    patch=json.loads(patch_path.read_text());pinmap=json.loads(pins_path.read_text());place=json.loads(placement_path.read_text())
    edit=json.loads((ROOT/st['accepted_edit_manifest']).read_text())
    if patch['base_gds_sha256']!=reference_sha:raise RuntimeError('tie patch reference hash mismatch')
    if edit.get('source_gds_sha256')!=reference_sha or edit.get('candidate_gds_sha256')!=source_sha:
        raise RuntimeError('metal checkpoint does not match its accepted edit manifest')
    def load(path):
        ly=db.Layout();ly.read(str(path));top=ly.cell(st['top'])
        if top is None:raise RuntimeError(f"top cell {st['top']} missing in {path}")
        return ly,top
    probe_layout,_=load(source);placement_dbu=probe_layout.dbu
    def u(x):
        if abs(x/rules.MFG_GRID-round(x/rules.MFG_GRID))>1e-6:raise RuntimeError(f'off manufacturing grid: {x}')
        return round(x/placement_dbu)
    def inst_signature(path):
        ly,top=load(path);out=[]
        for ir in top.each_inst():
            t=ir.trans
            out.append((ir.cell.name,t.rot,t.is_mirror(),t.disp.x,t.disp.y,
                        ir.a.x,ir.a.y,ir.b.x,ir.b.y,ir.na,ir.nb))
        return sorted(out)
    ref_instances=collections.Counter(inst_signature(reference));src_instances=collections.Counter(inst_signature(source))
    dx=src_instances-ref_instances;dr=ref_instances-src_instances
    expected_dx=collections.Counter();expected_dr=collections.Counter()
    for x,y in edit['via_centers_um']:
        common=('via_1$2',0,False,u(x),0,0,0,0,0,0)
        expected_dr[common[:3]+(u(x),u(edit['old_track_y_um']))+common[4:]]=1
        expected_dx[common[:3]+(u(x),u(edit['new_track_y_um']))+common[4:]]=1
    if dx!=expected_dx or dr!=expected_dr:
        raise RuntimeError(f'unexpected instance/placement changes; added={dx}, removed={dr}')
    instance_count=sum(src_instances.values())
    if instance_count!=2221:raise RuntimeError(f'unexpected placed/flattened instance array count: {instance_count}')
    actual_d=[p for p in pinmap.get(patch['intended_net'],[]) if p[:2]==['_542_','D']]
    if len(actual_d)!=1 or actual_d[0][2:]!=[1628.1,1640.7]:
        raise RuntimeError(f'constant pin differs from patch anchor: {actual_d}')

    ly,top=load(source);dbu=ly.dbu
    def probe_all_rails():
        l2n=db.LayoutToNetlist(db.RecursiveShapeIterator(ly,top,[]))
        layers={n:l2n.make_layer(ly.layer(*getattr(rules,n)),n) for n in ('M1','M2','V1','GC','CO')}
        for r in layers.values():l2n.connect(r)
        for a,b in [('M1','V1'),('V1','M2'),('GC','CO'),('CO','M1')]:l2n.connect(layers[a],layers[b])
        l2n.extract_netlist()
        lef=lef_parser.parse_lef(ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_cells.lef')
        item=next(i for row in place['rows'] for i in row if i['name']=='_542_')
        refs=[ir for ir in top.each_inst() if ir.cell.name==item['type'] and
              abs(ir.trans.disp.x*dbu-item['x'])<dbu and ir.dbbox().bottom<1640.7<ir.dbbox().top]
        if len(refs)!=1:raise RuntimeError(f'_542_ cell transform lookup ambiguous: {len(refs)}')
        ir=refs[0];labels={}
        for sh in ir.cell.shapes(ly.layer(*rules.M1_LBL)).each():
            if sh.is_text() and sh.text.string in ('vdd','vss'):
                p=ir.trans*db.Point(sh.text.trans.disp.x,sh.text.trans.disp.y)
                labels[sh.text.string]=(p.x*dbu,p.y*dbu)
        def node(layer,x,y):
            n=l2n.probe_net(layers[layer],db.Point(u(x),u(y)))
            return n.expanded_name() if n else None
        rails={name:node('M1',*xy) for name,xy in labels.items()}
        if not rails.get('vdd') or not rails.get('vss') or rails['vdd']==rails['vss']:
            raise RuntimeError(f'VDD/VSS label connectivity invalid: {labels} {rails}')
        on_rail={name:set() for name in rails}
        for intended,records in pinmap.items():
            for inst,pin,x,y in records:
                hit=node('M1',x,y) or node('M2',x,y)
                if hit is None:raise RuntimeError(f'actual pin has no metal: {inst}.{pin} ({intended})')
                for name,rail_net in rails.items():
                    if hit==rail_net:on_rail[name].add(intended)
        return labels,{k:sorted(v) for k,v in on_rail.items()}

    before_labels,before=probe_all_rails()
    if patch['intended_net'] in before['vdd']:raise RuntimeError('constant already tied before patch')
    # Insert exact polygon vertices, preserving concave merged route shapes.
    for name in ('M1','M2','V1'):
        layer=ly.layer(*getattr(rules,name))
        for coords in patch['added_polygons_um'][name]:
            pts=[db.Point(u(x),u(y)) for x,y in coords]
            if len(pts)<4:raise RuntimeError(f'invalid {name} patch polygon')
            top.shapes(layer).insert(db.Polygon(pts))
    after_labels,after=probe_all_rails()
    if set(after['vdd'])-set(before['vdd'])!={patch['intended_net']}:
        raise RuntimeError(f'VDD additions differ from the intended constant: {before} -> {after}')
    if before['vss']!=after['vss'] or before_labels!=after_labels:
        raise RuntimeError(f'VSS/rail labels changed: {before} -> {after}')
    dest=build/'routed_checkpoint.gds';ly.write(str(dest))
    if sha(source)!=source_sha or sha(reference)!=reference_sha:
        raise RuntimeError('an input checkpoint changed during patch application')
    if collections.Counter(inst_signature(dest))!=src_instances:raise RuntimeError('output instance placement changed')
    manifest={'status':'generated; full checks pending','source_gds':st['source_gds'],
      'source_gds_sha256':source_sha,'reference_gds':st['reference_gds'],
      'reference_gds_sha256':reference_sha,'patch_json':st['patch_json'],
      'patch_sha256':patch_sha,'actual_pin_map_sha256':pin_sha,
      'routing_shapes_sha256':shape_sha,'placement_sha256':sha(placement_path),
      'config_sha256':sha(design/'config.py'),'generator_sha256':sha(Path(__file__)),
      'toolchain_lock_sha256':sha(ROOT/'toolchain.lock.json'),'output_gds_sha256':sha(dest),
      'instance_placement_matches_accepted_metal_edit':True,
      'placement_delta_from_reference':{'only_via_cell':'via_1$2',
        'accepted_via_centers_um':edit['via_centers_um'],
        'reference_y_um':edit['old_track_y_um'],'accepted_y_um':edit['new_track_y_um']},'top_cell':st['top'],
      'instance_array_count':instance_count,'tie_anchor':patch['tie_from'],
      'via_centers_um':patch['via_centers_um'],'before_rail_signal_nets':before,
      'after_rail_signal_nets':after,'rail_connectivity':'PASS',
      'bbox_um':[top.dbbox().left,top.dbbox().bottom,top.dbbox().right,top.dbbox().top],
      'limitations':'Final connectivity and official drawing/mask DRC must be recorded before accepting this composed checkpoint.'}
    (build/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
