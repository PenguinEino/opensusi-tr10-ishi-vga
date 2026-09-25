#!/usr/bin/env python3
"""Read-only review of the submitted letter core, including all binary states.

This complements fresh official DRC/LVS/STA and the continuous RTL/gate test.
The vector evaluator checks the final mapped circuit, not a resynthesized RTL.
It does not model analog power-up, metastability, interconnect RC or PVT.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

import klayout.db as db
import numpy as np
from check_toolchain import ROOT, verify

sys.path.insert(0, str(ROOT/'tools/APRtools/apr'))
import lib_query
import lef_parser
import rules
from letter_animation_eco import extraction


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate(typ, inputs):
    if typ.startswith('BUF'):
        return inputs['A']
    if typ.startswith('INV'):
        return ~inputs['A']
    if typ == 'MUX2':
        return np.where(inputs['S'], inputs['B'], inputs['A'])
    if typ in ('XOR2', 'XNOR2'):
        value = inputs['A'] ^ inputs['B']
        return ~value if typ == 'XNOR2' else value
    if typ.startswith(('AND', 'NAND')):
        value = np.logical_and.reduce(list(inputs.values()))
        return ~value if typ.startswith('NAND') else value
    if typ.startswith(('OR', 'NOR')):
        value = np.logical_or.reduce(list(inputs.values()))
        return ~value if typ.startswith('NOR') else value
    raise RuntimeError('Unsupported gate '+typ)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    verify()
    sub = ROOT/'submission'
    manifest = json.loads((sub/'manifest.json').read_text())
    require(all(sha(sub/p) == digest for p, digest in manifest['files'].items()), 'Bundle changed')
    text = (sub/'source/ishi_vga_core_pnr.v').read_text()
    cells = [(t, n, dict((p, v.strip()) for p, v in re.findall(r'\.(\w+)\(([^)]+)\)', body)))
             for t, n, body in re.findall(r'^\s*(\w+)\s+(\S+)\s*\((.*?)\);', text, re.M | re.S) if t != 'module']
    ff = {pp['Q']: pp for typ, _, pp in cells if typ == 'DFF'}
    state = [f'h[{i}]' for i in range(7)] + [f'v[{i}]' for i in range(10)] + [f'anim_phase_{i}_' for i in range(7)]
    outputs = ['r', 'g', 'b', 'hsync', 'vsync']
    require(len(cells) == 241 and set(ff) == set(state+outputs), 'Unexpected mapped state')
    # Reject output feedback. Then arbitrary initial values of the five output
    # FFs do not enlarge the 24-bit state space whose next-state we check.
    known = {'clk'} | set(state) | {ff[q]['QB'] for q in state}
    pending = [(t, n, p) for t, n, p in cells if t != 'DFF']
    ordered = []
    while pending:
        progressed = False
        for cell in pending[:]:
            typ, name, pp = cell
            if all(net in known for pin, net in pp.items() if pin != 'Y'):
                known.add(pp['Y'])
                ordered.append(cell)
                pending.remove(cell)
                progressed = True
        require(progressed, 'Combinational loop, unsupported alias or output feedback')
    require(all(ff[q]['D'] in known and ff[q]['CK'] in known for q in ff), 'Unresolved FF input')
    h = np.arange(131072, dtype=np.uint32) % 128
    v = np.arange(131072, dtype=np.uint32) // 128
    nh = np.where(h == 100, 71, (h-1) % 128)
    nv = np.where(h == 100, np.where(v == 0, 500, (v+1) % 1024), v)
    reference = np.array([int(s, 16) for s in (sub/'tests/expected_states.hex').read_text().split()], dtype=np.uint8)
    require(len(reference) == len(h), 'Wrong all-state reference size')
    for phase in range(128):
        values = {'clk': np.zeros(len(h), dtype=bool)}
        for axis, data, count in [('h', h, 7), ('v', v, 10), ('phase', np.full(len(h), phase, dtype=np.uint32), 7)]:
            for i in range(count):
                q = f'anim_phase_{i}_' if axis == 'phase' else f'{axis}[{i}]'
                values[q] = ((data >> i) & 1).astype(bool)
                values[ff[q]['QB']] = ~values[q]
        for typ, name, pp in ordered:
            values[pp['Y']] = gate(typ, {p: values[n] for p, n in pp.items() if p != 'Y'})
        np_ = np.where((h == 100) & (v == 0), (phase+1) % 128, phase)
        for prefix, wanted, count in [('h', nh, 7), ('v', nv, 10), ('phase', np_, 7)]:
            for i in range(count):
                q = f'anim_phase_{i}_' if prefix == 'phase' else f'{prefix}[{i}]'
                require(np.array_equal(values[ff[q]['D']], ((wanted >> i) & 1).astype(bool)), f'Next state {q}, phase {phase}')
        expected = reference.copy()
        x = (71-h) % 128
        if phase < 64:
            expected[((reference & 7) == 4) & (x >= 8) & (x < 72) & ((x-8)//16 == phase//16)] |= 3
        observed = sum(values[ff[q]['D']].astype(np.uint8) * weight for q, weight in zip(outputs, [4, 2, 1, 8, 16]))
        require(np.array_equal(observed, expected), f'Output mismatch, phase {phase}')
    # Independently paint the intended normal raster from glyph and line data.
    frame = np.zeros((525, 100), dtype=np.uint8)
    frame[92:108, 8:72] = 3
    frame[396:412, 8:72] = 3
    frame[172:204, 8:72] = 1
    frame[300:332, 8:72] = 5
    frame[300:332, 48] = 0
    for rectangles in json.loads((ROOT/'experiments/a_metal_g_power/metal.json').read_text()).values():
        for x0, y0, x1, y1 in rectangles:
            frame[y0:y1, x0+8:x1+8] = 3
    glyphs = json.loads((ROOT/'experiments/a_half_grid64/glyphs.json').read_text())
    for i, letter in enumerate('ISHI'):
        for row, bits in enumerate(glyphs[letter]):
            for col, bit in enumerate(bits):
                if bit == '1':
                    frame[140+row*32:172+row*32, 8+i*16+col*2:10+i*16+col*2] = 4
    frame[:, :82] |= 8
    frame[:, 94:] |= 8
    frame[:490, :] |= 16
    frame[492:, :] |= 16
    frame_reference = np.array([int(s, 16) for s in (sub/'tests/expected_frame.hex').read_text().split()], dtype=np.uint8)
    require(np.array_equal(frame.ravel(), frame_reference), 'Independent raster mismatch')
    x, y = (71-h) % 128, (v-500) % 1024
    valid = (x < 100) & (y < 525)
    require(np.array_equal(reference[valid], frame[y[valid], x[valid]]), 'State/raster reference mismatch')
    # The next-state graph is now checked against every final gate D input.
    next_state = (nv*128+nh).astype(int)
    distance, cycles = {}, []
    for start in range(len(h)):
        path, seen, s = [], {}, start
        while s not in distance and s not in seen:
            seen[s] = len(path)
            path.append(s)
            s = int(next_state[s])
        if s in seen:
            begin = seen[s]
            cycles.append(len(path)-begin)
            distance.update((q, 0) for q in path[begin:])
            path = path[:begin]
        for q in reversed(path):
            distance[q] = distance[int(next_state[q])]+1
    require(cycles == [52500], 'Unexpected scan cycle')
    layout = db.Layout()
    layout.read(str(sub/'ishi_vga.gds'))
    top = layout.cell('ishi_vga_core')
    ports = json.loads((sub/'ports.json').read_text())
    box = top.dbbox()
    require(ports['bbox_um'] == [box.left, box.bottom, box.right, box.top], 'Port bbox mismatch')
    require(box.width() <= 1800 and box.height() <= 900, 'Budget exceeded')
    for p in ports['ports']:
        tag = p['layer']
        labels = [s.text for s in top.shapes(layout.layer(*getattr(rules, tag+'_LBL'))).each() if s.is_text() and s.text.string == p['name']]
        require(len(labels) == 1, 'Missing or duplicate label '+p['name'])
        xy = p['xy_um']
        require(np.allclose([labels[0].x*layout.dbu, labels[0].y*layout.dbu], xy, rtol=0, atol=layout.dbu/2), 'Label coordinate mismatch')
        px, py = (round(z/layout.dbu) for z in xy)
        metal = db.Region(top.begin_shapes_rec(layout.layer(*getattr(rules, tag))))
        require(not metal.interacting(db.Region(db.Box(px, py, px+1, py+1))).is_empty(), 'Port misses metal')
    library = db.Layout()
    library.read(str(ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_STDCELL.gds'))
    lef = lef_parser.parse_lef(ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_cells.lef')
    placement = json.loads((sub/'verification/placement.json').read_text())
    tags = {(ly.get_info(i).layer, ly.get_info(i).datatype)
            for ly in (layout, library) for i in ly.layer_indexes()}
    checked_cells = []
    for typ in sorted({c['type'] for row in placement['rows'] for c in row}):
        name = lef[typ]['foreign']
        for tag in tags:
            actual = db.Region(layout.cell(name).begin_shapes_rec(layout.layer(*tag)))
            expected = db.Region(library.cell(name).begin_shapes_rec(library.layer(*tag)))
            require((actual ^ expected).is_empty(), 'Library geometry differs: '+name)
        checked_cells.append(name)
    regions, connectivity = extraction(layout, top)
    port_components = []
    for p in ports['ports']:
        point = db.Point(*(round(v/layout.dbu) for v in p['xy_um']))
        node = connectivity.probe_net(regions[p['layer']], point)
        require(node is not None, 'Unconnected port '+p['name'])
        port_components.append(node.expanded_name())
    require(len(set(port_components)) == 8, 'Port short')
    lib = ROOT/'tools/APRtools/stdcell/v59_4/tr1um_typ_5v0_25c.lib'
    ck = lib_query.pin_cap(lib, 'DFF', 'CK')
    section = lib.read_text().split('  cell (BUF_X2) {', 1)[1].split('  cell (', 1)[0]
    limit = float(re.search(r'max_capacitance\s*:\s*([\d.]+)', section)[1])
    loads = {net: {'dffs': count, 'pin_cap_ff': round(count*ck, 3),
                   'max_cap_ff': limit, 'remaining_ff_before_wire': round(limit-count*ck, 3)}
             for net, count in sorted(Counter(pp['CK'] for pp in ff.values()).items())}
    inputs = [sub/'ishi_vga.gds', sub/'source/ishi_vga_core_pnr.v', sub/'source/tr1um_cells.v',
              sub/'tests/expected_states.hex', sub/'tests/expected_frame.hex', sub/'ports.json', lib,
              sub/'verification/placement.json', ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_STDCELL.gds',
              ROOT/'tools/APRtools/stdcell/v59_4/TR-1um_cells.lef',
              ROOT/'scripts/letter_animation_eco.py', ROOT/'tools/APRtools/apr/rules.py',
              ROOT/'tools/APRtools/apr/lib_query.py', ROOT/'tools/APRtools/apr/lef_parser.py',
              ROOT/'experiments/a_metal_g_power/metal.json', ROOT/'experiments/a_half_grid64/glyphs.json', Path(__file__)]
    result = {'status': 'PASS', 'gds_sha256': sha(sub/'ishi_vga.gds'),
              'binary_h_v_phase_states_checked': 16777216, 'output_ff_feedback': False,
              'independent_raster_match': True, 'scan_cycle_ticks': cycles[0],
              'max_ticks_into_scan_cycle': max(distance.values()), 'clock_loads': loads,
              'ports_match_gds_labels_and_metal': True,
              'distinct_electrical_port_components': len(set(port_components)),
              'pinned_library_cell_geometry_matches': checked_cells,
              'scope': 'Boolean final-netlist audit; no analog start-up/RC/PVT guarantee',
              'hashes': {str(p.relative_to(ROOT)): sha(p) for p in inputs}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'hashes'}, indent=2))


if __name__ == '__main__':
    main()
