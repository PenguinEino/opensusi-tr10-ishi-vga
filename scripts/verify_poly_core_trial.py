#!/usr/bin/env python3
"""Check the real GC edit and its clipped crossover connectivity independently."""
import json
import hashlib
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from check_toolchain import ROOT, verify
sys.path.insert(0, str(ROOT/'tools/APRtools/apr'))
import rules
import klayout.db as db


def report_items(path):
    tree = ET.parse(path)
    return sorted((i.findtext('category'), tuple(v.text for v in i.findall('./values/value')))
                  for i in tree.findall('./items/item'))


def local_nets(path, poly):
    ly = db.Layout()
    ly.read(str(path))
    tc = ly.cell('ishi_vga_core')
    # Clip actual full-hierarchy geometry, not hand-redrawn intended routes.
    coupon = db.Layout()
    coupon.dbu = ly.dbu
    top = coupon.create_cell('actual_crossover_crop')
    win = db.Box(1048000, 704000, 1085000, 717000)
    layers = {'M1': rules.M1, 'M2': rules.M2, 'V1': rules.V1,
              'GC': rules.GC, 'CO': rules.CO}
    for name, ld in layers.items():
        reg = db.Region(tc.begin_shapes_rec(ly.layer(*ld))) & db.Region(win)
        top.shapes(coupon.layer(*ld)).insert(reg)
    l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(coupon, top, []))
    r = {n: l2n.make_layer(coupon.layer(*ld), n) for n, ld in layers.items()}
    for n in ('M1', 'M2', 'V1'):
        l2n.connect(r[n])
    l2n.connect(r['M1'], r['V1'])
    l2n.connect(r['V1'], r['M2'])
    if poly:
        for n in ('GC', 'CO'):
            l2n.connect(r[n])
        l2n.connect(r['GC'], r['CO'])
        l2n.connect(r['CO'], r['M1'])
    l2n.extract_netlist()
    points = {'jump_left': (1050, 708), 'jump_right': (1083, 708),
              'cross_left': (1061.1, 708), 'cross_right': (1071.9, 708)}
    ids = {}
    for name, (x, y) in points.items():
        net = l2n.probe_net(r['M1'], db.Point(round(x/ly.dbu), round(y/ly.dbu)))
        assert net is not None, name
        ids[name] = net.expanded_name()
    return ids


def main():
    verify()
    out = ROOT/'experiments/poly_core/build'
    source = ROOT/'experiments/phys_desc5/build/postrepair_compacted.gds'
    trial = out/'poly_core_trial.gds'
    before = local_nets(source, True)
    after = local_nets(trial, True)
    omitted = local_nets(trial, False)
    assert len(set(before.values())) == 1, before
    assert after['jump_left'] == after['jump_right'], after
    assert after['cross_left'] == after['cross_right'], after
    assert after['jump_left'] != after['cross_left'], after
    assert len(set(omitted.values())) == 3, omitted
    base_errors = report_items(ROOT/'experiments/routing_audit/postrepair_baseline.lyrdb')
    trial_errors = report_items(out/'poly_core_trial.lyrdb')
    assert base_errors == trial_errors, 'New/different official DRC markers'
    base_mask = ROOT/'experiments/phys_desc5/build/postrepair_compacted_mdp.lyrdb'
    trial_mask = out/'poly_core_trial_mdp.lyrdb'
    assert base_mask.exists() and trial_mask.exists(), 'Run both official MDP checks first'
    base_mask_errors, trial_mask_errors = report_items(base_mask), report_items(trial_mask)
    assert base_mask_errors == trial_mask_errors, 'New/different mask DRC markers'
    regions = []
    for p in (source, trial):
        ly = db.Layout(); ly.read(str(p)); t = ly.cell('ishi_vga_core')
        regions.append({(info.layer, info.datatype): db.Region(t.begin_shapes_rec(ly.layer(info))).merged()
                        for info in ly.layer_infos()})
    changed = []
    for ld in sorted(regions[0].keys() | regions[1].keys()):
        if not (regions[0].get(ld, db.Region()) ^ regions[1].get(ld, db.Region())).is_empty():
            changed.append(ld)
    assert set(changed) == {rules.GC, rules.CO, rules.M1}, changed
    result = {'local_crossover_check': 'PASS', 'before_local_components': before,
        'after_local_components_including_GC_CO': after,
        'negative_control_GC_omitted': omitted, 'changed_layers': changed,
        'official_drc_same_markers_as_input': True,
        'official_drc_remaining': len(trial_errors),
        'mask_drc_same_markers_as_input': True, 'mask_drc_remaining': len(trial_mask_errors),
        'sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (source,trial,base_mask,trial_mask,Path(__file__))},
        'limitations': 'Local crop proves the edited crossover only. Full-core connectivity and circuit LVS are separate; remaining baseline errors are not waived.'}
    (out/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
