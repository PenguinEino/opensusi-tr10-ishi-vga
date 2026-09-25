#!/usr/bin/env python3
"""Connect the reset synchronizer's constant-one D pin to its real VDD rail."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys

from check_toolchain import ROOT, verify


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    verify()
    design = ROOT/'experiments/constant_tie'
    design.mkdir(exist_ok=True)
    config = design/'config.py'
    if not config.exists():
        text = (ROOT/'experiments/phys_desc5/config.py').read_text()
        settings = {'input_gds': 'experiments/phys_desc5/build/postrepair_compacted.gds',
                    'actual_pins': 'experiments/routing_audit/actual_pin_map.json',
                    'placement': 'experiments/phys_desc5/layout/placement.json',
                    'instance': '_542_', 'pin': 'D', 'literal': "1'h1", 'rail': 'vdd',
                    'search_x_tracks': 8, 'search_y_offsets_um': [-3.4,-5.4,-8.1,-10.8,3.4,5.4,8.1,10.8]}
        config.write_text(text.replace('finalize(globals())',
            f'CONSTANT_TIE = {settings!r}\n\nfinalize(globals())'))
    os.environ['APRTOOLS'] = str(ROOT/'tools/APRtools')
    os.environ['TR1UM_PDK'] = str(ROOT/'tools/TR-1um')
    sys.path[:0] = [str(design), str(ROOT/'tools/APRtools/apr')]
    import rules
    import klayout.db as db
    cfg = runpy.run_path(str(config)); st = cfg['CONSTANT_TIE']
    build = design/'build'; build.mkdir(exist_ok=True)
    source = ROOT/st['input_gds']
    source_hash = sha(source)
    pinmap = json.loads((ROOT/st['actual_pins']).read_text())
    place = json.loads((ROOT/st['placement']).read_text())
    item = next(i for row in place['rows'] for i in row if i['name'] == st['instance'])
    assert item['pins'][st['pin']]['net'] == st['literal']
    _inst, _pin, px, py = next(p for p in pinmap[st['literal']]
                              if p[:2] == [st['instance'], st['pin']])
    ly = db.Layout(); ly.read(str(source)); top = ly.cell(cfg['TOP_CELL_NAME'])
    refs = [ir for ir in top.each_inst() if ir.cell.name == item['type']
            and abs(ir.trans.disp.x*ly.dbu-item['x']) < ly.dbu
            and ir.dbbox().bottom < py < ir.dbbox().top]
    assert len(refs) == 1
    ir = refs[0]
    labels = {}
    for s in ir.cell.shapes(ly.layer(*rules.M1_LBL)).each():
        if s.is_text() and s.text.string in ('vdd', 'vss'):
            # Text displacement is a Vector; transform a Point to include the
            # instance translation as well as orientation.
            p = ir.trans * db.Point(s.text.trans.disp.x, s.text.trans.disp.y)
            labels[s.text.string] = (p.x*ly.dbu, p.y*ly.dbu)
    rail_y = labels[st['rail']][1]

    def u(x):
        assert abs(x/rules.MFG_GRID-round(x/rules.MFG_GRID)) < 1e-6
        return round(x/ly.dbu)

    def box(layer, x0, y0, x1, y1):
        top.shapes(ly.layer(*layer)).insert(db.Box(u(x0), u(y0), u(x1), u(y1)))

    def make_l2n():
        l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, top, []))
        ls = {n: l2n.make_layer(ly.layer(*getattr(rules, n)), n)
              for n in ('M1', 'M2', 'V1', 'GC', 'CO')}
        for r in ls.values(): l2n.connect(r)
        for a,b in [('M1','V1'), ('V1','M2'), ('GC','CO'), ('CO','M1')]:
            l2n.connect(ls[a], ls[b])
        l2n.extract_netlist()
        return l2n, ls

    def connectivity():
        l2n, ls = make_l2n()
        def node(layer, x, y):
            n = l2n.probe_net(ls[layer], db.Point(u(x), u(y)))
            return n.expanded_name() if n else None
        rail = {n: node('M1', *xy) for n,xy in labels.items()}
        assert rail['vdd'] and rail['vss'] and rail['vdd'] != rail['vss'], (labels,rail)
        nets = {n: set() for n in rail}
        for net, pins in pinmap.items():
            for _inst, _pn, x,y in pins:
                hit = node('M1', x,y) or node('M2', x,y)
                assert hit is not None, (_inst,_pn)
                for name in rail:
                    if hit == rail[name]: nets[name].add(net)
        return {n: sorted(v) for n,v in nets.items()}

    before = connectivity()
    assert st['literal'] not in before[st['rail']]
    # Preserve the first tie attempt: it connected D to VDD, but introduced a
    # V1.CO DRC marker and is not an acceptable result.
    import shutil
    if (build/'constant_tied.gds').exists() and not (build/'constant_tied_failed_v1.gds').exists():
        for src, dst in [('constant_tied.gds','constant_tied_failed_v1.gds'),
                         ('manifest.json','manifest_failed_v1.json'),
                         ('landing_search.json','landing_search_failed_v1.json'),
                         ('constant_tied.lyrdb','constant_tied_failed_v1.lyrdb'),
                         ('pdk_drc.log','pdk_drc_failed_v1.log'),
                         ('generate.log','generate_failed_v1.log')]:
            if (build/src).exists(): shutil.copyfile(build/src,build/dst)

    # Identify a VDD-connected M2 mesh strap by connectivity probing. Route
    # from D into the empty top channel, then cross on M1 to that strap.
    def rr(layer): return db.Region(top.begin_shapes_rec(ly.layer(*layer))).merged()
    def rect(x0,y0,x1,y1): return db.Region(db.Box(u(x0),u(y0),u(x1),u(y1)))
    def box_um(b,dbu): return [round(b.left*dbu,4),round(b.bottom*dbu,4),round(b.right*dbu,4),round(b.top*dbu,4)]
    m1,m2,co,gc,gr,v1 = [rr(getattr(rules,n)) for n in ('M1','M2','CO','GC','GR','V1')]
    l2n,ls=make_l2n()
    def probe(layer,x,y):
        n=l2n.probe_net(ls[layer],db.Point(u(x),u(y)))
        return n.expanded_name() if n else None
    vdd_name=probe('M1',*labels['vdd']);vss_name=probe('M1',*labels['vss'])
    assert vdd_name and vss_name and vdd_name!=vss_name
    vdd_m1=db.Region();vdd_m2=db.Region();straps=[]
    for tag,region in [('M1',m1),('M2',m2)]:
        for p in region.each():
            b=p.bbox();cx=(b.left+b.right)*ly.dbu/2;cy=(b.bottom+b.top)*ly.dbu/2
            if probe(tag,cx,cy)==vdd_name:
                (vdd_m1 if tag=='M1' else vdd_m2).insert(p)
                if tag=='M2' and b.top*ly.dbu>=top.dbbox().top-0.1:
                    straps.append({'x_um':round(cx,3),'bbox_um':box_um(b,ly.dbu)})
    assert straps,'No VDD-connected M2 strap reaches the core top'
    strap=min(straps,key=lambda q:abs(q['x_um']-px));sx=strap['x_um']
    ownpin=m2.interacting(rect(px-0.05,py-0.05,px+0.05,py+0.05))
    channel_y=st.get('top_channel_y_um',1758.6)
    via_half=rules.V1_CUT/2;m1pad=rules.V1_CUT+2*rules.V1_ENC_M1
    m2pad=rules.V1_CUT+2*rules.V1_ENC_M2
    m1wire=rules.M1_WIDTH_MIN;m2wire=rules.M2_WIRE_WIDTH
    # V1.CO is not in APRtools rules.py; read the pinned executable rule.
    from poly_core_trial import deck_limit
    co_space, _ = deck_limit(ROOT/'tools/TR-1um/libs.tech/klayout/tech/drc/run.drc','V1.CO')
    x=px
    strap_y=round(strap['bbox_um'][3]+m2pad/2-0.3,3)
    m2_escape=(rect(x-m2wire/2,py-m2wire/2,x+m2wire/2,py+m2wire/2)
               +rect(x-m2wire/2,py-m2wire/2,x+m2wire/2,channel_y+m2wire/2)).merged()
    m1_cross=(rect(min(x,sx)-m1wire/2,channel_y-m1wire/2,max(x,sx)+m1wire/2,channel_y+m1wire/2)
               +rect(sx-m1wire/2,min(channel_y,strap_y)-m1wire/2,sx+m1wire/2,max(channel_y,strap_y)+m1wire/2)
               +rect(x-m1pad/2,channel_y-m1pad/2,x+m1pad/2,channel_y+m1pad/2)
               +rect(sx-m1pad/2,strap_y-m1pad/2,sx+m1pad/2,strap_y+m1pad/2)).merged()
    m2_landing_a=rect(x-m2pad/2,channel_y-m2pad/2,x+m2pad/2,channel_y+m2pad/2)
    m2_landing_b=rect(sx-m2pad/2,strap_y-m2pad/2,sx+m2pad/2,strap_y+m2pad/2)
    m2_added=m2_escape+m2_landing_a+m2_landing_b
    v1_added=(rect(x-via_half,channel_y-via_half,x+via_half,channel_y+via_half)
              +rect(sx-via_half,strap_y-via_half,sx+via_half,strap_y+via_half))
    # The respective intended D/VDD M2 components are excluded. All other
    # existing metal, vias, CO, GC and GR are checked with the locked rules.
    checks=[('M1',m1_cross,m1-vdd_m1,rules.M1_SPACE_MIN),
            ('M2',m2_added,m2-ownpin-vdd_m2,rules.M2_SPACE_MIN),
            ('CO',v1_added,co,co_space),
            ('GA',v1_added,gc+gr,rules.V1_GA_SPACE_MIN),
            ('V1',v1_added,v1,rules.V1_SPACE_MIN)]
    blocked=[tag for tag,new,old,gap in checks if not (new.sized(u(gap))&old).is_empty()]
    assert not (m2_landing_a&m2_escape).is_empty()
    assert not (m2_landing_b&vdd_m2).is_empty()
    (build/'landing_search.json').write_text(json.dumps({'selected_vdd_strap':strap,
        'top_channel_y_um':channel_y,'via_centers_um':[[x,channel_y],[sx,strap_y]],
        'blocked_by':blocked},indent=2)+'\n')
    assert not blocked,f'Top-channel route is blocked by {blocked}'
    for region,layer in [(m1_cross,rules.M1),(m2_added,rules.M2),(v1_added,rules.V1)]:
        for polygon in region.each():top.shapes(ly.layer(*layer)).insert(polygon)
    after = connectivity()
    assert set(after[st['rail']])-set(before[st['rail']]) == {st['literal']}, (before,after)
    assert before['vss'] == after['vss'], (before,after)
    dest = build/'constant_tied.gds'; ly.write(str(dest))
    assert sha(source) == source_hash
    manifest = {'input_gds': st['input_gds'], 'input_sha256': source_hash,
        'output_sha256': sha(dest), 'config_sha256': sha(config),
        'generator_sha256': sha(Path(__file__)), 'toolchain_lock_sha256': sha(ROOT/'toolchain.lock.json'),
        'actual_pin_map_sha256': sha(ROOT/st['actual_pins']),
        'tie': st, 'pin_xy_um': [px,py], 'via_xy_um': [[x,channel_y],[sx,strap_y]],
        'vdd_m2_strap': strap,
        'added_geometry_bbox_um': {'M1':[box_um(p.bbox(),ly.dbu) for p in m1_cross.each()],
                                   'M2':[box_um(p.bbox(),ly.dbu) for p in m2_added.each()],
                                   'V1':[box_um(p.bbox(),ly.dbu) for p in v1_added.each()]},
        'rail_labels_xy_um': labels, 'before_rail_signal_nets': before, 'after_rail_signal_nets': after,
        'rail_connectivity_assertions': 'PASS', 'size_um': [top.dbbox().width(),top.dbbox().height()],
        'limitations': 'Constant tie only; unrelated baseline signal shorts remain. Final power/frame integration is separate.'}
    (build/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    def polygons_um(region):
        result=[]
        for p in region.each():
            if p.holes()!=0: raise RuntimeError('Patch polygon unexpectedly has holes')
            pts=[[round(q.x*ly.dbu,4),round(q.y*ly.dbu,4)] for q in p.each_point_hull()]
            result.append(pts)
        return result
    exact_polygons={ 'M1':polygons_um(m1_cross),'M2':polygons_um(m2_added),
                     'V1':polygons_um(v1_added) }
    patch = {'base_gds':st['input_gds'],'base_gds_sha256':source_hash,
        'top_cell':cfg['TOP_CELL_NAME'],'intended_net':st['literal'],
        'tie_from':f"{st['instance']}.{st['pin']}",'rail':'VDD',
        'added_polygons_um':exact_polygons,
        'added_geometry_bbox_um':manifest['added_geometry_bbox_um'],
        'via_centers_um':manifest['via_xy_um'],
        'note':'Polygon vertices preserve the exact concave route shape. Insert these top-cell polygons into a same-placement candidate and rerun connectivity plus official DRC.'}
    (build/'constant_tie_patch.json').write_text(json.dumps(patch,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


if __name__ == '__main__': main()
