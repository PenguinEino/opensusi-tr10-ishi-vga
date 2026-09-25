#!/usr/bin/env python3
"""Fail closed on dependency, asset, or environment drift; not DRC/LVS/STA."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()

def verify():
    lock = json.loads((ROOT / 'toolchain.lock.json').read_text())
    errors = []
    for name, spec in lock['repositories'].items():
        repo = ROOT / spec['path']
        try:
            if git(repo, 'rev-parse', 'HEAD') != spec['commit']:
                errors.append(f'{name}: HEAD differs from locked commit')
            if git(repo, 'remote', 'get-url', 'origin') != spec['url']:
                errors.append(f'{name}: origin differs from locked URL')
            allowed = {}
            for patch in lock.get('patches', []):
                if patch['repository'] != name: continue
                p = ROOT / patch['path']
                if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != patch['sha256']:
                    errors.append(f'{name}: recorded patch changed')
                allowed.update(patch['files'])
            changed = set(git(repo, 'diff', 'HEAD', '--name-only').splitlines())
            if changed != set(allowed):
                errors.append(f'{name}: tracked changes differ from recorded patches')
            for rel, digest in allowed.items():
                p = repo / rel
                if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                    errors.append(f'{name}: patched file differs: {rel}')
        except (subprocess.CalledProcessError, FileNotFoundError):
            errors.append(f'{name}: missing or invalid checkout')
    for key, asset in lock['assets'].items():
        p = ROOT / asset['path']
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != asset['sha256']:
            errors.append(f'{key}: missing or changed asset: {asset["path"]}')
    for key, value in os.environ.items():
        if key.startswith(('APR_', 'TD4_', 'I2C_')):
            errors.append(f'{key}: inherited design override is forbidden; put settings in config.py')
    for key, rel in [('APRTOOLS', 'tools/APRtools'), ('TR1UM_PDK', 'tools/TR-1um')]:
        if key in os.environ and Path(os.environ[key]).resolve() != (ROOT / rel).resolve():
            errors.append(f'{key}: points outside the locked checkout')
    if errors:
        raise RuntimeError('\n'.join(errors))
    return lock

def main():
    try:
        lock = verify()
    except RuntimeError as exc:
        print(f'TOOLCHAIN CHECK FAILED\n{exc}', file=sys.stderr)
        return 1
    print('PASS: pinned repositories, exact recorded patches, asset SHA256, environment')
    for name, spec in lock['repositories'].items():
        print(f'  {name}: {spec["commit"]}')
    for name in ('cell_gds', 'cell_lef', 'liberty', 'frame_gds', 'frame_lvs'):
        print(f'  {name}: {lock["assets"][name]["path"]}')
    print('This is provenance verification only; synthesis/DRC/LVS/STA have not been certified.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
