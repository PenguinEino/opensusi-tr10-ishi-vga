#!/usr/bin/env python3
"""Copy a verified route candidate into an ancestor-audit checkpoint, without rewriting GDS."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
from check_toolchain import ROOT, verify


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--design-root', type=Path, required=True)
    args = ap.parse_args()
    design = args.design_root.resolve()
    verify()
    settings = None
    for node in ast.parse((design / 'config.py').read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CHECKPOINT_SOURCE' for t in node.targets):
            settings = ast.literal_eval(node.value)
    if settings is None:
        raise ValueError('literal CHECKPOINT_SOURCE required')
    source = ROOT / settings['gds']
    report = ROOT / settings['verification']
    assert sha(source) == settings['sha256']
    assert sha(report) == settings['verification_sha256']
    verified = json.loads(report.read_text())
    assert verified['status'] == 'ACCEPTED' and all(verified['checks'].values())
    assert verified['candidate_sha256'] == sha(source)
    assert not verified['new_pairs']
    build = design / 'build'
    build.mkdir(parents=True, exist_ok=True)
    dest = build / 'candidate.gds'
    shutil.copyfile(source, dest)
    assert sha(dest) == settings['sha256'] == sha(source)
    manifest = {
        'status': 'copied verified candidate; ancestor audit and circuit LVS are separate checks',
        'selected_source': settings, 'candidate_sha256': sha(dest),
        'config_sha256': sha(design / 'config.py'),
        'generator_sha256': sha(Path(__file__)),
        'toolchain_lock_sha256': sha(ROOT / 'toolchain.lock.json'),
    }
    (build / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(dest, sha(dest))


if __name__ == '__main__':
    main()
