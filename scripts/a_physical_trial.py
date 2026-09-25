#!/usr/bin/env python3
"""Isolated A core-only placement/routing/compaction measurement.

Output is diagnostic, not a DRC/LVS-qualified deliverable. Upstream entry points
always go through run_apr.py; process constants remain in pinned rules.py.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from a_logo_trial import ROOT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source')
    ap.add_argument('name')
    ap.add_argument('--rows', type=int, required=True)
    ap.add_argument('--seed', type=int, default=4)
    ap.add_argument('--restarts', type=int, default=160)
    ap.add_argument('--prl', type=int, default=10)
    ap.add_argument('--pad-weight', type=float, default=1.0)
    a = ap.parse_args()
    assert a.source.startswith('a_') and a.name.startswith('a_')
    assert '/' not in a.source + a.name
    src, dst = [ROOT / 'experiments' / n for n in (a.source, a.name)]
    assert not dst.exists(), 'Do not overwrite a physical trial'
    for sub in ('build', 'out', 'tests'):
        (dst / sub).mkdir(parents=True, exist_ok=True)
    for f in ('ishi_vga_core.v', 'ishi_logo.v', 'out/ishi_vga_core_pnr.v', 'tests/expected_frame.hex'):
        (dst / f).write_bytes((src / f).read_bytes())
    cfg = (src / 'config.py').read_text()
    values = {'N_ROWS': str(a.rows), 'CORE_WIDTH_TRACKS': '328',
              'CH_HEIGHTS': f'[140.4] + [151.2] * {a.rows-1} + [162.0]',
              'ROUTE_CH_HEIGHTS': f'[216.0] + [900.0] * {a.rows-1} + [216.0]',
              'PLACE_SEED': str(a.seed), 'PLACE_RESTARTS': str(a.restarts),
              'PAD_WEIGHT': str(a.pad_weight),
              'ROUTING_KNOBS': repr({'PRL_MIN_PINS': a.prl, 'SPAN_LANE_PACK': False})}
    for key, value in values.items():
        cfg, n = re.subn('^' + key + r'\s*=.*$', key + ' = ' + value, cfg, flags=re.M)
        assert n == 1, key
    (dst / 'config.py').write_text(cfg)
    inputs = [Path(__file__), ROOT / 'toolchain.lock.json', src / 'source_manifest.json',
              src / 'out/ishi_vga_core_pnr.v', dst / 'config.py', dst / 'ishi_logo.v', dst / 'ishi_vga_core.v']
    manifest = {'source': a.source, 'physical': vars(a), 'sha256': {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}}
    (dst / 'source_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    steps = [('apr/place.py', [], 'place.log'), ('apr/verify_placement.py', [], 'verify_placement.log'),
             ('apr/route.py', ['--to', '6'], 'route_step6.log'),
             ('apr/squeeze_channels.py', ['--in-gds', 'layout/step6/route_step_2_routed_raw.gds',
              '-o', 'build/diagnostic_compacted.gds', '--pin-map-in', 'layout/pin_map.json',
              '--pin-map-out', 'build/diagnostic_pins.json', '--net-shapes-in', 'layout/net_shapes.json',
              '--net-shapes-out', 'build/diagnostic_shapes.json'], 'diagnostic_compaction.log')]
    status = []
    for entry, args, logname in steps:
        with (dst / 'build' / logname).open('w') as log:
            r = subprocess.run([str(ROOT / '.venv/bin/python'), str(ROOT / 'scripts/run_apr.py'),
                                '--design-root', str(dst), entry, *args], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        status.append({'entry': entry, 'args': args, 'log': logname, 'returncode': r.returncode})
        print(a.name, entry, r.returncode, flush=True)
        if r.returncode:
            break
    report = {'status': 'DIAGNOSTIC_ONLY', 'steps': status, 'source_manifest': manifest,
              'limitations': 'No short/open repair, power-tie completion, port escapes, frame, ring, official DRC/LVS, or post-route timing.'}
    gds = dst / 'build/diagnostic_compacted.gds'
    if gds.exists():
        import klayout.db as kdb
        ly = kdb.Layout(); ly.read(str(gds)); b = ly.cell('ishi_vga_core').dbbox()
        report.update(bbox_um=[b.left, b.bottom, b.right, b.top], width_um=b.width(), height_um=b.height(),
                      gds_sha256=hashlib.sha256(gds.read_bytes()).hexdigest(), fits_1800=b.width() <= 1800 and b.height() <= 1800)
    placement = dst / 'layout/step1/place_step1_rows.json'
    if placement.exists():
        p = json.loads(placement.read_text())
        report.update(placement_cut=p.get('cut'), channel_crossings=p.get('channel_crossings'))
    (dst / 'build/physical_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('source_manifest', 'steps')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
