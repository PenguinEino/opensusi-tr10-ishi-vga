#!/usr/bin/env python3
"""Place the adopted name and reduced penguin as isolated drawing metal.

The penguin is sampled from the original polygons onto a manufacturable pixel
grid. Tiny original components (including both pupils) are retained; diagonal
point contacts are bridged by one pixel. Functional geometry is untouched.
"""
import argparse
import ast
import json
from pathlib import Path
import sys
import klayout.db as db
import numpy as np
from check_toolchain import ROOT, verify
from letter_animation_eco import sha

sys.path.insert(0, str(ROOT/'tools/APRtools/apr'))
import rules


def settings(path):
    return next(ast.literal_eval(n.value) for n in ast.parse(path.read_text()).body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SILICON_ART' for t in n.targets))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--design-root', type=Path, default=ROOT/'experiments/a_letter_silicon_art')
    a = ap.parse_args()
    verify()
    d = a.design_root.resolve()
    st = settings(d/'config.py')
    for key, digest in [('source_gds', 'source_sha256'), ('penguin_gds', 'penguin_sha256'), ('font_json', 'font_sha256')]:
        assert sha(ROOT/st[key]) == st[digest], key
    ly = db.Layout()
    ly.read(str(ROOT/st['source_gds']))
    top = ly.cell('ishi_vga_core')
    before = top.bbox()
    old = db.Layout()
    old.read(str(ROOT/st['penguin_gds']))
    source = db.Region(old.cell('SVG_METAL2_ART').shapes(old.layer(*rules.M2)))
    scale, pixel, n = st['penguin_scale'], st['penguin_pixel_um'], st['penguin_grid_cells']
    bits = np.zeros((n, n), dtype=bool)
    components = list(source.each())
    for y in range(n):
        for x in range(n):
            point = db.Point(round((x+.5-n/2)*pixel/scale/old.dbu), round((y+.5-n/2)*pixel/scale/old.dbu))
            bits[y, x] = any(poly.inside(point) for poly in components)
    # Preserve tiny source components that fall between the sampling centers.
    retained = []
    for poly in components:
        center = poly.bbox().center()
        if poly.area()*old.dbu**2 < (pixel/scale)**2:
            x = int(np.floor(center.x*old.dbu*scale/pixel+n/2))
            y = int(np.floor(center.y*old.dbu*scale/pixel+n/2))
            assert 0 <= x < n and 0 <= y < n
            bits[y, x] = True
            retained.append([x, y])
    bridges = []
    while True:
        changed = False
        for y in range(n-1):
            for x in range(n-1):
                aa, bb, cc, dd = bits[y, x], bits[y, x+1], bits[y+1, x], bits[y+1, x+1]
                if aa == dd and bb == cc and aa != bb:
                    xx = x+1 if aa else x
                    bits[y, xx] = True
                    bridges.append([xx, y])
                    changed = True
        if not changed:
            break
    art = db.Region()
    u = lambda x: round(x/ly.dbu)
    cx, cy = st['penguin_center_um']
    for y, x in zip(*np.where(bits)):
        art.insert(db.Box(*(u(v) for v in [cx+(x-n/2)*pixel, cy+(y-n/2)*pixel,
                                          cx+(x+1-n/2)*pixel, cy+(y+1-n/2)*pixel])))
    font = json.loads((ROOT/st['font_json']).read_text())
    for text, left, bottom in st['text_lines']:
        for i, letter in enumerate(text):
            for row, pattern in enumerate(font[letter]):
                for col, bit in enumerate(pattern):
                    if bit == '1':
                        x = left+i*st['text_advance_um']+col*st['text_pixel_um']
                        y = bottom+(6-row)*st['text_pixel_um']
                        art.insert(db.Box(u(x), u(y), u(x+st['text_pixel_um']), u(y+st['text_pixel_um'])))
    art = art.merged()
    assert not art.width_check(u(getattr(rules, st['layer']+'_WIDTH_MIN'))).count()
    assert not art.space_check(u(getattr(rules, st['layer']+'_SPACE_MIN'))).count()
    for tag in ('M1', 'M2', 'V1'):
        geometry = db.Region(top.begin_shapes_rec(ly.layer(*getattr(rules, tag)))).merged()
        assert (art.sized(u(st['clearance_um'])) & geometry).is_empty(), 'Art too close to '+tag
    assert (art-db.Region(before)).is_empty()
    for p in art.each():
        for ring in [list(p.each_point_hull())]+[list(p.each_point_hole(i)) for i in range(p.holes())]:
            assert all(v.x % u(rules.MFG_GRID) == 0 and v.y % u(rules.MFG_GRID) == 0 for v in ring)
    cell = ly.create_cell(st['cell'])
    cell.shapes(ly.layer(*getattr(rules, st['layer']))).insert(art)
    top.insert(db.CellInstArray(cell.cell_index(), db.Trans()))
    assert top.bbox() == before
    out = d/'build'
    out.mkdir(parents=True, exist_ok=True)
    save = db.SaveLayoutOptions()
    save.gds2_write_timestamps = False
    ly.write(str(out/'candidate.gds'), save)
    report = {'status': 'GEOMETRY_CHECKED_NOT_SIGNED_OFF', 'gds_sha256': sha(out/'candidate.gds'),
              'source_sha256': st['source_sha256'], 'art_bbox_um': str(cell.dbbox()),
              'art_layer': st['layer'], 'clearance_to_functional_m1_m2_via_um': st['clearance_um'],
              'penguin_retained_small_pixels': retained, 'penguin_bridged_pixels': bridges,
              'settings': st, 'hashes': {str(p.relative_to(ROOT)): sha(p) for p in
              [Path(__file__), d/'config.py', ROOT/st['source_gds'], ROOT/st['penguin_gds'], ROOT/st['font_json']]}}
    (out/'art_geometry.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('settings', 'hashes')}, indent=2))


if __name__ == '__main__':
    main()
