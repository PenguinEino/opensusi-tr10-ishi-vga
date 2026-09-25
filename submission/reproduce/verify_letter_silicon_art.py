#!/usr/bin/env python3
"""Requalify the isolated artwork against the frozen, fully checked core."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import klayout.db as db
from add_letter_silicon_art import settings
from check_toolchain import ROOT, verify
from letter_animation_eco import sha, pinmap, lef_parser, rules
from power_spice_check import blocks
from prune_route_vias import connectivity
from validate_route_candidate import report_markers


def extraction_signature(path):
    text = path.read_text()
    circuits = blocks(text)
    top = circuits.pop('ishi_vga_core')
    locations, current = {}, None
    for line in text.splitlines():
        m = re.fullmatch(r'\* cell instance (\S+) (.+)', line)
        if m:
            current = (m[1], m[2])
        tokens = line.split()
        if tokens and tokens[0].startswith('X') and current and tokens[0] == 'X'+current[0]:
            locations[tokens[0]] = current[1]
    nets = defaultdict(list)
    for p in top['ports']:
        nets[p].append(('PORT', p))
    instances = []
    for tokens in top['elements']:
        assert tokens[0].startswith('X') and tokens[0] in locations
        name, typ = tokens[0], tokens[-1]
        identity = (typ, locations[name])
        instances.append(identity)
        pins = circuits[typ]['ports']
        assert len(tokens[1:-1]) == len(pins)
        for pin, node in zip(pins, tokens[1:-1]):
            nets[node].append((typ, locations[name], pin))
    assert len(instances) == len(set(instances))
    # Exact cell parameters and internal terminal roles, not a device-count-only
    # check. Anonymous top net/instance IDs may change after GDS serialization.
    return {'ports': top['ports'], 'instances': sorted(instances),
            'nets': sorted(sorted(endpoints) for endpoints in nets.values()), 'cells': circuits}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--design-root', type=Path, default=ROOT/'experiments/a_letter_silicon_art')
    args = ap.parse_args()
    verify()
    d = args.design_root.resolve()
    b = d/'build'
    st = settings(d/'config.py')
    geometry = json.loads((b/'art_geometry.json').read_text())
    assert all(sha(ROOT/p) == digest for p, digest in geometry['hashes'].items())
    assert geometry['gds_sha256'] == sha(b/'candidate.gds')
    old, new = db.Layout(), db.Layout()
    old.read(str(ROOT/st['source_gds']))
    new.read(str(b/'candidate.gds'))
    ot, nt = old.cell('ishi_vga_core'), new.cell('ishi_vga_core')
    art = new.cell(st['cell'])
    assert old.dbu == new.dbu == .001 and ot.bbox() == nt.bbox()
    ar = db.Region(art.begin_shapes_rec(new.layer(*getattr(rules, st['layer'])))).merged()
    tags = {(ly.get_info(i).layer, ly.get_info(i).datatype) for ly in (old, new) for i in ly.layer_indexes()}
    for tag in tags:
        before = db.Region(ot.begin_shapes_rec(old.layer(*tag)))
        after = db.Region(nt.begin_shapes_rec(new.layer(*tag)))
        if tag == getattr(rules, st['layer']):
            assert (before & ar).is_empty() and ((after-before) ^ ar).is_empty() and (before-after).is_empty()
        else:
            assert (before ^ after).is_empty(), tag
    for tag in ('M1', 'M2', 'V1'):
        before = db.Region(ot.begin_shapes_rec(old.layer(*getattr(rules, tag))))
        assert (ar.sized(round(st['clearance_um']/new.dbu)) & before).is_empty(), tag
    def labels(ly, top):
        return sorted((ly.get_info(i).to_s(), s.text.to_s()) for i in ly.layer_indexes() for s in top.shapes(i).each() if s.is_text())
    assert labels(old, ot) == labels(new, nt)
    assert not report_markers(b/'drawing.lyrdb')
    base = ROOT/'release/ishi_vga_letter_scan_core'
    assert report_markers(b/'candidate_mdp.lyrdb') == report_markers(base/'verification/candidate_mdp.lyrdb')
    lvs = db.LayoutVsSchematic()
    lvs.read(str(b/'core.lvsdb'))
    xref, ports = lvs.xref(), []
    assert 'strict port mode' in (b/'lvs.log').read_text()
    for pair in xref.each_circuit_pair():
        assert pair.first() and pair.second() and pair.status() == xref.Match
        if pair.first().name == nt.name:
            for pin in xref.each_pin_pair(pair):
                assert pin.first() and pin.second() and pin.status() == xref.Match
                assert pin.first().name().lower() == pin.second().name().lower()
                ports.append(pin.first().name().lower())
            assert all(p.status() == xref.Match for p in xref.each_net_pair(pair))
            assert all(p.status() == xref.Match for p in xref.each_subcircuit_pair(pair))
    assert sorted(ports) == sorted(['clk', 'r', 'g', 'b', 'hsync', 'vsync', 'vdd', 'vss'])
    assert extraction_signature(base/'ishi_vga.extracted') == extraction_signature(b/'core.extracted')
    lef = lef_parser.parse_lef(ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_cells.lef')
    ys = sorted({round(i.trans.disp.y*new.dbu, 4) for i in nt.each_inst() if i.cell.name == 'DFF'})
    pins, layers = pinmap(json.loads((base/'verification/placement.json').read_text()), lef, ys)
    result = connectivity(new, nt, pins, layers)
    assert not result['pairs'] and not result['opens'] and not result['missing']
    assert result['power_component_counts'] == {'vss': 1, 'vdd': 1}
    assert result['rail_signal_nets'] == {'vss': [], 'vdd': []}
    paths = [Path(__file__), ROOT/'scripts/add_letter_silicon_art.py', d/'config.py',
             b/'candidate.gds', b/'core.extracted', b/'art_geometry.json', b/'core.lvsdb',
             b/'drawing.lyrdb', b/'candidate_mdp.lyrdb', b/'lvs.log', b/'drc.log',
             base/'ishi_vga.gds', base/'ishi_vga.extracted', base/'verification/placement.json']
    report = {'status': 'ART_CORE_VERIFIED', 'gds_sha256': sha(b/'candidate.gds'),
              'base_gds_sha256': sha(base/'ishi_vga.gds'), 'extracted_sha256': sha(b/'core.extracted'),
              'all_original_functional_geometry_preserved': True, 'named_ports_preserved': ports,
              'extraction_electrically_identical': True,
              'electrical_comparison': 'exact cell parameters/internal terminals; top nets as named-port/physical-instance pin endpoint sets',
              'drawing_drc': 0, 'strict_lvs': 'PASS', 'inherited_mask_warnings': 1,
              'size_um': [nt.dbbox().width(), nt.dbbox().height()],
              'art_bbox_um': geometry['art_bbox_um'], 'art_layer': st['layer'],
              'art_clearance_um': st['clearance_um'],
              'signal_opens': 0, 'signal_shorts': 0, 'missing_signal_pins': 0,
              'power_component_counts': result['power_component_counts'],
              'scope': 'isolated artwork; no wire RC/PVT/frame integration; functional RTL/gate/STA evidence retained by equivalence',
              'hashes': {str(p.relative_to(ROOT)): sha(p) for p in paths}}
    (b/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'hashes'}, indent=2))


if __name__ == '__main__':
    main()
