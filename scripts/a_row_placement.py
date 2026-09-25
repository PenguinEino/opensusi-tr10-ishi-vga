#!/usr/bin/env python3
"""A placement experiment, independent row search with pinned upstream packing.

No upstream source modification/monkey-patching. Import unmodified packing and
ordering helpers, then run verification/routing CLI via the normal wrapper.
"""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from check_toolchain import ROOT, verify


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def context(d):
    os.environ['APRTOOLS'] = str(ROOT / 'tools/APRtools')
    os.environ['TR1UM_PDK'] = str(ROOT / 'tools/TR-1um')
    os.chdir(d)
    sys.path.insert(0, str(ROOT / 'tools/APRtools/apr'))
    import apr_path
    import config
    import place
    return config, place


def prepare(name, source, restarts, steps, seed, spread):
    dst, src = ROOT / 'experiments' / name, ROOT / 'experiments' / source
    assert not dst.exists(), 'Do not overwrite a recorded trial'
    for sub in ('build', 'out', 'tests'): (dst / sub).mkdir(parents=True, exist_ok=True)
    for f in ('ishi_vga_core.v', 'ishi_logo.v', 'out/ishi_vga_core_pnr.v', 'tests/expected_frame.hex'):
        (dst / f).write_bytes((src / f).read_bytes())
    cfg = (src / 'config.py').read_text()
    settings = {'source': source, 'restarts': restarts, 'steps_per_restart': steps,
                'seed': seed, 'temperature_start': 4.0, 'temperature_end': 0.02,
                'spread_weight': spread, 'order_passes': 80,
                'max_width_average_factor': 1.025}
    cfg = cfg.replace('finalize(globals())', f'ROW_OPT = {settings!r}\nfinalize(globals())')
    cfg = re.sub(r'^PAD_WEIGHT = .*$', 'PAD_WEIGHT = 0.0', cfg, flags=re.M)
    (dst / 'config.py').write_text(cfg)
    paths = [src / 'source_manifest.json', src / 'layout/placement.json', src / 'layout/row_assignment.json',
             src / 'out/ishi_vga_core_pnr.v', dst / 'config.py', Path(__file__), ROOT / 'scripts/row_anneal.cpp',
             ROOT / 'toolchain.lock.json', ROOT / 'tools/APRtools/apr/place.py']
    manifest = {'source': source, 'sha256': {str(p.relative_to(ROOT)): sha(p) for p in paths}}
    (dst / 'source_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(dst.relative_to(ROOT))


def solve(d):
    cfg, place = context(d)
    st = cfg.ROW_OPT
    src = ROOT / 'experiments' / st['source']
    cells, macro, width, cellof, net_cells, ports, macro_pin = place.load(cfg.NET_PATH, cfg.CELL_INFO)
    assert macro is None
    names = sorted(width); ids = {n: i for i, n in enumerate(names)}
    initial = json.loads((src / 'layout/row_assignment.json').read_text())
    assert set(initial) == set(names)
    unit = cfg.SITE_UM
    wi = [round(width[n] / unit) for n in names]
    assert all(abs(w * unit - width[n]) < 1e-6 for w, n in zip(wi, names))
    usable = cfg.ROW_WIDTH_UM - sum(w for _, w, _ in place.fixed_blocks(cfg.ROW_WIDTH_UM))
    cap = min(math.floor(usable / unit), math.floor(sum(wi) / cfg.N_ROWS * st['max_width_average_factor']))
    actual_initial_max = max(sum(wi[i] for i, n in enumerate(names) if initial[n] == r) for r in range(cfg.N_ROWS))
    cap = max(cap, actual_initial_max)
    assert cap * unit <= usable + 1e-6
    nets = [sorted(ids[n] for n in ns if n in ids) for _, ns in sorted(net_cells.items())]
    nets = [ns for ns in nets if len(ns) > 1]
    params = [len(names), len(nets), cfg.N_ROWS, cap, st['restarts'], st['steps_per_restart'], st['seed'],
              st['temperature_start'], st['temperature_end'], st['spread_weight']]
    lines = [' '.join(map(str, params)), ' '.join(map(str, wi)), ' '.join(str(initial[n]) for n in names)]
    lines += [' '.join(map(str, [len(ns), *ns])) for ns in nets]
    graph = d / 'build/row_graph.txt'; graph.write_text('\n'.join(lines) + '\n')
    exe = d / 'build/row_anneal'
    subprocess.run(['g++', '-O3', '-std=c++17', str(ROOT / 'scripts/row_anneal.cpp'), '-o', str(exe)], check=True)
    with (d / 'build/anneal.log').open('w') as log:
        subprocess.run([str(exe), str(graph), str(d / 'build/assignment.txt'), str(d / 'build/restart')],
                       check=True, stdout=log, stderr=subprocess.STDOUT)
    result = (d / 'build/assignment.txt').read_text().splitlines()
    score, restart = map(int, result[0].split())
    values = list(map(int, result[1].split()))
    assert len(values) == len(names) and all(0 <= r < cfg.N_ROWS for r in values)
    assignment = dict(zip(names, values))
    widths = place.row_widths(assignment, width, cfg.N_ROWS)
    assert max(widths) <= cap * unit + 1e-6
    baseline_cut = place.cut_cost(initial, net_cells)
    cut = place.cut_cost(assignment, net_cells)
    spread = sum(max(0, len({assignment[n] for n in ns if n in assignment}) - 1) for ns in net_cells.values())
    assert score == cut + st['spread_weight'] * spread
    info = json.loads(Path(cfg.CELL_INFO).read_text())
    ys, _ = cfg.row_y()
    order, hpwl = place.order_rows(assignment, width, net_cells, ports, ys, cfg.N_ROWS, {},
                                   passes=st['order_passes'], seed=st['seed'], prefs={})
    cross = place.crossings(assignment, net_cells, ports, cfg.N_ROWS)
    packed = [place.pack_row(row, width, cellof, cfg.ROW_WIDTH_UM, True, True, cfg.PLACE_FILL_MODE) for row in order]
    assert all(abs(end-cfg.ROW_WIDTH_UM)<1e-6 for _,end in packed)
    # Only the unchanged upstream packer creates TAP/FILLs and cell transforms.
    placed = [p[0] for p in packed]
    assert sorted(i for row in placed for _, i, _, _ in row if i) == names
    extra = {'assign': assignment, 'cut': cut, 'channel_crossings': cross, 'hpwl_um': hpwl,
             'tap_x': place.tap_positions(cfg.ROW_WIDTH_UM),
             'pri_x': [x for x, _, kind in place.fixed_blocks(cfg.ROW_WIDTH_UM) if kind == 'pri'],
             'row_end_x': [p[1] for p in packed]}
    place.dump(4, 'fill', placed, ys, None, info, extra)
    (d / 'layout/row_assignment.json').write_text(json.dumps(assignment, indent=2) + '\n')
    report = {'baseline_span_sum': baseline_cut, 'optimized_span_sum': cut, 'score': score,
              'restart': restart, 'cell_row_widths_um': widths, 'channel_crossings': cross,
              'packing': 'unmodified pinned APRtools place.pack_row/dump',
              'sha256': {str(p.relative_to(ROOT)): sha(p) for p in [graph, exe, d / 'build/assignment.txt',
                         d / 'layout/step4/place_step4_fill.json', d / 'layout/step4/place_step4_fill.gds']}}
    (d / 'build/row_optimization.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


def route(d):
    steps = [('apr/verify_placement.py', [], 'verify_placement.log'),
             ('apr/route.py', ['--to', '6'], 'route_step6.log'),
             ('apr/squeeze_channels.py', ['--in-gds', 'layout/step6/route_step_2_routed_raw.gds',
              '-o', 'build/diagnostic_compacted.gds', '--pin-map-in', 'layout/pin_map.json',
              '--pin-map-out', 'build/diagnostic_pins.json', '--net-shapes-in', 'layout/net_shapes.json',
              '--net-shapes-out', 'build/diagnostic_shapes.json'], 'diagnostic_compaction.log')]
    status = []
    for entry, args, logname in steps:
        with (d / 'build' / logname).open('w') as log:
            rc = subprocess.call([str(ROOT / '.venv/bin/python'), str(ROOT / 'scripts/run_apr.py'),
                                  '--design-root', str(d), entry, *args], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        status.append({'entry': entry, 'args': args, 'returncode': rc})
        if rc: raise RuntimeError(logname)
    import klayout.db as kdb
    gds = d / 'build/diagnostic_compacted.gds'
    ly = kdb.Layout(); ly.read(str(gds)); box = ly.cell('ishi_vga_core').dbbox()
    result = {'status': 'DIAGNOSTIC_ONLY', 'width_um': box.width(), 'height_um': box.height(),
              'gds_sha256': sha(gds), 'steps': status,
              'limitations': 'No short repair, constant tie, final port escapes, frame integration, DRC/LVS or routed timing yet.'}
    (d / 'build/physical_report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['prepare', 'solve', 'route'])
    ap.add_argument('name')
    ap.add_argument('--source', default='a_phys_h63_alt6')
    ap.add_argument('--restarts', type=int, default=12)
    ap.add_argument('--steps', type=int, default=4000000)
    ap.add_argument('--seed', type=int, default=11)
    ap.add_argument('--spread', type=int, default=0)
    a = ap.parse_args()
    assert a.name.startswith('a_') and '/' not in a.name
    verify()
    if a.action == 'prepare': prepare(a.name, a.source, a.restarts, a.steps, a.seed, a.spread)
    else:
        if os.environ.get('PYTHONHASHSEED') != '0':
            os.environ['PYTHONHASHSEED'] = '0'
            os.execv(sys.executable, [sys.executable, *sys.argv])
        (solve if a.action == 'solve' else route)(ROOT / 'experiments' / a.name)
