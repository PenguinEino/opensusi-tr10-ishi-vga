#!/usr/bin/env python3
"""Normalize explicit scalar constant pins for pinned mklvsnet, without GDS input.

The pinned exporter treats 1'h1 as a SPICE node, which is not a supply tie.
Only configured instance/pin literals are changed in a derived LVS-only input.
The original synthesized Verilog and all upstream dependencies remain intact.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from check_toolchain import ROOT, verify
sys.path.insert(0, str(ROOT / 'tools/APRtools/apr'))
import rules


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--design-root', type=Path, required=True)
    args = ap.parse_args()
    design = args.design_root.resolve()
    verify()
    cfg_path = design / 'config.py'
    cfg = None
    for n in ast.parse(cfg_path.read_text()).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'LVS_REFERENCE' for t in n.targets):
            cfg = ast.literal_eval(n.value)
    if cfg is None:
        raise ValueError('literal LVS_REFERENCE required')
    original = ROOT / cfg['netlist']
    placement = ROOT / cfg['placement']
    previous_spice = ROOT / cfg['unadapted_spice']
    assert sha(original) == cfg['netlist_sha256']
    assert sha(placement) == cfg['placement_sha256']
    assert sha(previous_spice) == cfg['unadapted_spice_sha256']
    paths = [original, placement, previous_spice, cfg_path, Path(__file__),
             ROOT / 'tools/APRtools/apr/mklvsnet.py', ROOT / 'tools/APRtools/apr/rules.py',
             ROOT / 'scripts/run_apr.py', ROOT / 'toolchain.lock.json']
    paths += sorted((ROOT / 'tools/APRtools/stdcell/v59_4/simulation').glob('*.spice'))
    before = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    text = original.read_text()
    changes = []
    expected_spice = previous_spice.read_text()
    for item in cfg['constant_pins']:
        typ, inst, pin, literal = (item[k] for k in ('cell', 'instance', 'pin', 'literal'))
        value = re.fullmatch(r"1'[bhd]([01])", literal, re.I)
        if value is None:
            raise ValueError('only explicit known one-bit constants are supported')
        rail = rules.PWR_NET if value[1] == '1' else rules.GND_NET
        pattern = re.compile(r'\b' + re.escape(typ) + r'\s+' + re.escape(inst) + r'\s*\((.*?)\)\s*;', re.S)
        found = list(pattern.finditer(text))
        assert len(found) == 1, (typ, inst, 'instance must occur exactly once')
        m = found[0]
        pin_pattern = re.compile(r'(\.' + re.escape(pin) + r'\s*\(\s*)' + re.escape(literal) + r'(\s*\))')
        body, count = pin_pattern.subn(lambda p: p[1] + rail + p[2], m[1])
        assert count == 1, (inst, pin, literal, count)
        text = text[:m.start(1)] + body + text[m.end(1):]
        # Independently verify the exact expected SPICE token and port position
        # using the pinned standard-cell source definition, not the GDS.
        cell_spice = ROOT / 'tools/APRtools/stdcell/v59_4/simulation' / (typ + '.spice')
        decl = re.search(r'(?im)^\s*\.subckt\s+' + re.escape(typ) + r'\s+([^\n]+)', cell_spice.read_text())
        assert decl
        pin_index = decl[1].split().index(pin)
        lines = expected_spice.splitlines(keepends=True)
        hits = [i for i, line in enumerate(lines) if line.split() and line.split()[0].lower() == ('X' + inst).lower()]
        assert len(hits) == 1
        i = hits[0]; tokens = lines[i].split()
        assert tokens[-1] == typ and tokens[1 + pin_index] == literal
        tokens[1 + pin_index] = rail
        old_line = lines[i].rstrip('\n'); lines[i] = ' '.join(tokens) + '\n'
        expected_spice = ''.join(lines)
        changes.append({**item, 'rail': rail, 'before_spice': old_line, 'after_spice': lines[i].rstrip('\n')})
    # Every other byte of the synthesized input is preserved, including unused
    # aliases. The derived file is only for the LVS exporter, never simulation.
    build = design / 'build'; build.mkdir(parents=True, exist_ok=True)
    normalized = build / 'core_lvs_input.v'; normalized.write_text(text)
    output = build / 'ishi_vga_core.spice'
    cmd = [sys.executable, str(ROOT / 'scripts/run_apr.py'), '--design-root', str(design),
           'apr/mklvsnet.py', '--netlist', str(normalized), '--placement', str(placement),
           '--out', str(output), '--top', cfg['top']]
    run = subprocess.run(cmd, text=True, capture_output=True)
    (build / 'reference.log').write_text(run.stdout + run.stderr)
    if run.returncode:
        raise RuntimeError('upstream reference generation failed; see reference.log')
    def circuit_lines(s):
        return [ln for ln in s.splitlines() if ln.strip() and not ln.lstrip().startswith('*')]
    assert circuit_lines(output.read_text()) == circuit_lines(expected_spice), 'unexpected reference change'
    assert before == {str(p.relative_to(ROOT)): sha(p) for p in paths}, 'input changed during run'
    verify()
    report = {'status': 'ACCEPTED', 'purpose': 'independent LVS source; no GDS or extracted layout used',
              'command': cmd, 'constant_pin_changes': changes, 'input_hashes': before,
              'normalized_netlist_sha256': sha(normalized), 'reference_sha256': sha(output),
              'all_other_spice_statements_unchanged': True}
    (build / 'reference_manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'reference': str(output.relative_to(ROOT)), 'sha256': sha(output), 'changes': changes}, indent=2))


if __name__ == '__main__':
    main()
