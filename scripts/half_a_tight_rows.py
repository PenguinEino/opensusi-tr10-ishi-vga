#!/usr/bin/env python3
"""Five-row exact-A packing with explicit, reproducible balance constraints.

This supplements the prior placement experiment without changing frozen scripts
or any upstream dependency. Width is a design choice in site units, not a copied
process rule. Source and derivative manifests are kept separately.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from a_row_placement import ROOT, prepare
from check_toolchain import verify


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def seed():
    src = ROOT / 'experiments/a_half_a_direct4_phys5'
    dst = ROOT / 'experiments/a_half_a_direct4_tight5'
    assert not dst.exists()
    for sub in ['out','build','tests']: (dst / sub).mkdir(parents=True, exist_ok=True)
    for f in ['ishi_vga_core.v','ishi_logo.v','out/ishi_vga_core_pnr.v','tests/expected_frame.hex']:
        (dst / f).write_bytes((src / f).read_bytes())
    cfg = (src / 'config.py').read_text()
    for key, value in {'CORE_WIDTH_TRACKS':'330', 'PLACE_BALANCE_TOL':'0.005',
                       'PLACE_RESTARTS':'40', 'PLACE_SEED':'7'}.items():
        cfg, n = re.subn(r'^'+key+r' = .*$', key+' = '+value, cfg, flags=re.M)
        assert n == 1
    (dst / 'config.py').write_text(cfg)
    paths = [Path(__file__), src / 'source_manifest.json', src / 'config.py', dst / 'config.py',
             *[dst / f for f in ['ishi_vga_core.v','ishi_logo.v','out/ishi_vga_core_pnr.v','tests/expected_frame.hex']]]
    (dst / 'source_manifest.json').write_text(json.dumps({'source':str(src.relative_to(ROOT)),
        'scope':'placement seed only; 330 sites, tight balance; five rows',
        'sha256':{str(p.relative_to(ROOT)):sha(p) for p in paths}}, indent=2)+'\n')
    for entry, name in [('apr/place.py','place.log'),('apr/verify_placement.py','verify_placement.log')]:
        with (dst / 'build' / name).open('w') as log:
            subprocess.run([str(ROOT / '.venv/bin/python'),str(ROOT / 'scripts/run_apr.py'),
                '--design-root',str(dst),entry],check=True,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    print(dst.name)


def anneal_prepare():
    name = 'a_half_a_direct4_anneal5'
    prepare(name, 'a_half_a_direct4_tight5', 8, 2000000, 11, 0)
    dst = ROOT / 'experiments' / name
    # Constrain the row widths before any solve. Retain the original prepare
    # result too, so this explicit design override has a complete audit trail.
    manifest_path = dst / 'source_manifest.json'
    original = dst / 'prepare_manifest.json'
    original.write_bytes(manifest_path.read_bytes())
    cfg = (dst / 'config.py').read_text()
    assert cfg.count("'max_width_average_factor': 1.025") == 1
    (dst / 'config.py').write_text(cfg.replace("'max_width_average_factor': 1.025",
                                              "'max_width_average_factor': 1.005"))
    manifest = json.loads(manifest_path.read_text())
    manifest['design_override'] = {'max_width_average_factor':1.005}
    for p in [Path(__file__), original, dst / 'config.py']:
        manifest['sha256'][str(p.relative_to(ROOT))] = sha(p)
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')


if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['seed','prepare']);args=ap.parse_args()
    verify()
    (seed if args.action == 'seed' else anneal_prepare)()
