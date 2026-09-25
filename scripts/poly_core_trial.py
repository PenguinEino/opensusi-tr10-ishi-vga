#!/usr/bin/env python3
"""One bounded GC crossover on the real core; dependencies remain unmodified.

This is a geometry experiment, not a general router or a qualified RC model.
The input checkpoint remains immutable. Run with the project's .venv Python.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import sys

from check_toolchain import ROOT, verify


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deck_limit(deck, rule):
    """Read a missing rule from the pinned executable deck; fail if ambiguous."""
    lines = [s for s in deck.read_text().splitlines() if f"output('{rule}:" in s
             and re.search(r'<\s*[0-9.]', s.split('.output')[0])]
    assert len(lines) == 1, (rule, lines)
    numbers = re.findall(r"<\s*([0-9.]+)", lines[0].split('.output')[0])
    assert len(numbers) == 1, (rule, lines)
    return float(numbers[0]), lines[0]


def main():
    verify()
    design = ROOT / 'experiments/poly_core'
    design.mkdir(exist_ok=True)
    base = ROOT / 'experiments/phys_desc5'
    config = design / 'config.py'
    # Trial dimensions are design settings; process constants come from rules/deck.
    if not config.exists():
        settings = {
            'source_design': 'experiments/phys_desc5',
            'input_gds': 'build/postrepair_compacted.gds',
            'input_shapes': 'build/postrepair_shapes.json',
            'input_pins': 'build/postrepair_pins.json',
            'net': '_079_', 'shape_index': 1,
            'contacts_x_um': [1053.0, 1080.0],
            'detour_y_offset_um': 2.7,
            'gc_width_multiple_of_min': 1,
        }
        text = (base / 'config.py').read_text()
        assert text.count('finalize(globals())') == 1
        config.write_text(text.replace('finalize(globals())',
            f'POLY_TRIAL = {settings!r}\n\nfinalize(globals())'))
    os.environ['APRTOOLS'] = str(ROOT / 'tools/APRtools')
    os.environ['TR1UM_PDK'] = str(ROOT / 'tools/TR-1um')
    sys.path[:0] = [str(design), str(ROOT / 'tools/APRtools/apr')]
    import rules
    import klayout.db as db
    cfg = runpy.run_path(str(config))
    st = cfg['POLY_TRIAL']
    source = ROOT / st['source_design']
    files = {k: source / st[k] for k in ('input_gds', 'input_shapes', 'input_pins')}
    hashes = {k: sha(v) for k, v in files.items()}
    build = design / 'build'
    build.mkdir(exist_ok=True)
    deck = ROOT / 'tools/TR-1um/libs.tech/klayout/tech/drc/run.drc'
    gc_enc, gc_line = deck_limit(deck, 'CO.GC')
    m1_enc, m1_line = deck_limit(deck, 'M1.CO')
    ly = db.Layout()
    ly.read(str(files['input_gds']))
    top = ly.cell(cfg['TOP_CELL_NAME'])
    dbu = ly.dbu

    def u(x):
        assert abs(x / rules.MFG_GRID - round(x / rules.MFG_GRID)) < 1e-6, x
        return round(x / dbu)

    def box(x0, y0, x1, y1):
        return db.Box(u(x0), u(y0), u(x1), u(y1))

    def region(layer):
        return db.Region(top.begin_shapes_rec(ly.layer(*layer))).merged()

    before = {name: region(getattr(rules, name)) for name in ('M1', 'GC', 'CO', 'AP', 'AN')}
    shapes = json.loads(files['input_shapes'].read_text())
    net, ix = st['net'], st['shape_index']
    layer, x0, y0, x1, y1 = shapes[net][ix]
    assert layer == 'M1' and x1 - x0 > y1 - y0
    y = round((y0 + y1) / 2, 6)
    a, b = st['contacts_x_um']
    ydet = y + st['detour_y_offset_um']
    assert x0 < a < b < x1
    target = box(x0, y0, x1, y1)
    m1_idx = ly.layer(*rules.M1)
    found = [s for s in top.shapes(m1_idx).each() if s.is_box() and s.box == target]
    assert len(found) == 1, f'Expected exact owned top-level rectangle, got {len(found)}'
    found[0].delete()
    del shapes[net][ix]
    added = {name: db.Region() for name in ('M1', 'GC', 'CO')}

    def add(name, coords):
        rect = box(*coords)
        top.shapes(ly.layer(*getattr(rules, name))).insert(rect)
        shapes[net].append([name, *[round(c, 6) for c in coords]])
        added[name].insert(rect)

    add('M1', (x0, y0, a, y1))
    add('M1', (b, y0, x1, y1))
    contact_half = rules.CO_SIZE / 2
    gc_half = contact_half + gc_enc
    m1_half = contact_half + m1_enc
    for x in (a, b):
        for name, half in [('M1', m1_half), ('GC', gc_half), ('CO', contact_half)]:
            add(name, (x - half, y - half, x + half, y + half))
    w = rules.GC_WIDTH_MIN * st['gc_width_multiple_of_min']
    half = w / 2
    # Explicit overlapping rectangles avoid path end-extension ambiguities.
    # Carry the contact width through each elbow: a narrow stem beside a
    # 2.6 um contact landing creates a sub-1.2 um concave notch at this offset.
    add('GC', (a-gc_half, min(y, ydet)-half, a+gc_half, max(y, ydet)+half))
    add('GC', (a-half, ydet-half, b+half, ydet+half))
    add('GC', (b-gc_half, min(y, ydet)-half, b+gc_half, max(y, ydet)+half))
    added_gc = added['GC'].merged()
    assert (added_gc & (before['AP'] + before['AN'])).is_empty(), 'Would create an unintended MOS'
    assert (added_gc & before['GC']).is_empty(), 'Would touch preexisting gates'
    output = build / 'poly_core_trial.gds'
    ly.write(str(output))
    (build / 'net_shapes.json').write_text(json.dumps(shapes, indent=2) + '\n')
    shutil.copyfile(files['input_pins'], build / 'routing_anchors.json')
    assert hashes == {k: sha(v) for k, v in files.items()}, 'Input changed during experiment'
    bb = top.dbbox()
    manifest = {
        'status': 'experimental; full core still has unresolved metal shorts',
        'input_sha256': hashes, 'output_sha256': sha(output),
        'config_sha256': sha(config), 'generator_sha256': sha(Path(__file__)),
        'toolchain_lock_sha256': sha(ROOT/'toolchain.lock.json'),
        'deck_sha256': sha(deck), 'settings': st,
        'rule_sources': {'CO.GC': gc_line, 'M1.CO': m1_line,
                        'others': 'tools/APRtools/apr/rules.py'},
        'bbox_um': [bb.left, bb.bottom, bb.right, bb.top],
        'size_um': [bb.width(), bb.height()],
        'gc_centerline_length_um': b-a+2*abs(ydet-y), 'gc_width_um': w,
        'gc_area_um2': added_gc.area()*dbu*dbu,
        'new_contact_count': 2,
        'new_gc_over_active_area_um2': 0,
        'changed_layers': ['M1', 'GC', 'CO'],
        'verification_caveat': 'routing_anchors.json is inherited routing bookkeeping, not independently reconstructed cell pins. M1/M2-only verification cannot verify GC continuity.'
    }
    (build/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
