#!/usr/bin/env python3
"""Record strict official core LVS, checking the lvsdb rather than exit status."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

import klayout.db as db
from check_toolchain import ROOT, verify


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--design-root', type=Path, required=True)
    ap.add_argument('--gds', type=Path, required=True)
    ap.add_argument('--route-audit', type=Path, required=True)
    ap.add_argument('--labels', type=Path, required=True)
    args = ap.parse_args(); verify()
    design = args.design_root.resolve(); build = design / 'build'
    cfg = None
    for n in ast.parse((design / 'config.py').read_text()).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'LVS_REFERENCE' for t in n.targets):
            cfg = ast.literal_eval(n.value)
    assert cfg is not None
    top_name = cfg['top']
    ref = build / 'ishi_vga_core.spice'
    source_manifest = build / 'reference_manifest.json'
    rm = json.loads(source_manifest.read_text())
    assert rm['status'] == 'ACCEPTED' and rm['reference_sha256'] == sha(ref)
    assert all(sha(ROOT / p) == h for p, h in rm['input_hashes'].items())
    ports = re.search(r'(?im)^\.subckt\s+' + re.escape(top_name) + r'\s+([^\n]+)', ref.read_text())[1].split()
    route = json.loads(args.route_audit.read_text())
    labels = json.loads(args.labels.read_text())
    assert route['status'] == labels['status'] == 'ACCEPTED'
    assert all(route['checks'].values()) and all(labels['checks'].values())
    assert route['candidate_pair_count'] == 0 and not route['new_pairs']
    assert route['candidate_sha256'] == labels['hashes']['source_gds']
    assert sha(args.gds) == labels['hashes']['candidate_gds']
    assert labels['reference_spice_ports'] == ports
    report = build / 'core.lvsdb'; log_path = build / 'core_lvs.log'
    log = log_path.read_text()
    assert 'strict port mode' in log and 'flag_missing_ports enabled' in log
    assert 'Congratulations! Netlists match.' in log and "Netlists don't match" not in log
    lvs = db.LayoutVsSchematic(); lvs.read(str(report)); x = lvs.xref()
    pairs = list(x.each_circuit_pair()); summary = []
    top_pair = None
    for p in pairs:
        a, b = p.first(), p.second()
        assert a and b and p.status() == x.Match, 'unmatched circuit in official lvsdb'
        summary.append({'layout': a.name, 'reference': b.name, 'status': str(p.status())})
        if a.name == top_name:
            assert top_pair is None
            top_pair = p
    assert top_pair is not None
    pin_pairs = []
    for p in x.each_pin_pair(top_pair):
        assert p.first() and p.second() and p.status() == x.Match
        a, b = p.first().name(), p.second().name()
        assert a.lower() == b.lower()
        pin_pairs.append([a, b])
    assert sorted(a.lower() for a, b in pin_pairs) == sorted(s.lower() for s in ports)
    assert all(p.status() == x.Match for p in x.each_net_pair(top_pair))
    assert all(p.status() == x.Match for p in x.each_subcircuit_pair(top_pair))
    paths = [args.gds.resolve(), args.route_audit.resolve(), args.labels.resolve(), ref, source_manifest,
             report, log_path, design / 'config.py', Path(__file__).resolve(), ROOT / 'toolchain.lock.json',
             ROOT / 'tools/APRtools/apr/lvs_pdk.py', ROOT / 'scripts/run_apr.py']
    paths += sorted((ROOT / 'tools/TR-1um/libs.tech/klayout/tech/lvs').glob('*.lvs'))
    paths += [ROOT / 'tools/TR-1um/libs.tech/klayout/tech/drc/00_Layers.drc',
              ROOT / 'tools/TR-1um/libs.tech/klayout/tech/drc/02_Device.drc']
    result = {'status': 'PASS', 'scope': 'strict official core LVS; frame/pads and PEX are not included',
              'gds': str(args.gds.resolve().relative_to(ROOT)), 'gds_sha256': sha(args.gds),
              'reference': str(ref.relative_to(ROOT)), 'reference_sha256': sha(ref),
              'top': top_name, 'strict_ports': True, 'matched_port_count': len(pin_pairs),
              'circuit_pairs': summary, 'top_pin_pairs': pin_pairs,
              'all_top_nets_match': True, 'all_top_subcircuits_match': True,
              'route_audit_pairs': route['candidate_pair_count'],
              'drawing_markers': labels['drc']['candidate']['drawing_count'],
              'mask_markers': labels['drc']['candidate']['mdp_count'],
              'verification_command': [sys.executable, *sys.argv],
              'hashes': {str(p.relative_to(ROOT)): sha(p) for p in paths}}
    dest = build / 'lvs_verification.json'
    dest.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'scope', 'matched_port_count', 'route_audit_pairs', 'drawing_markers', 'mask_markers')}, indent=2))


if __name__ == '__main__':
    main()
