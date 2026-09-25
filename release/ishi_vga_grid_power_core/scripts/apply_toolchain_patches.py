#!/usr/bin/env python3
"""Apply only the reviewed lock-file patch to the exact pinned upstream tree."""
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
lock=json.loads((ROOT/'toolchain.lock.json').read_text())
for patch in lock.get('patches',[]):
    spec=lock['repositories'][patch['repository']]
    repo=ROOT/spec['path']; path=ROOT/patch['path']
    def git(*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
    if git('rev-parse','HEAD') != spec['commit']: raise RuntimeError('Wrong upstream revision')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=patch['sha256']: raise RuntimeError('Patch changed')
    if all((repo/p).exists() and hashlib.sha256((repo/p).read_bytes()).hexdigest()==h for p,h in patch['files'].items()):
        continue
    if git('status','--porcelain','--untracked-files=no'): raise RuntimeError('Unrecorded edits; refusing to overwrite')
    subprocess.run(['git','-C',str(repo),'apply','--check',str(path)],check=True)
    subprocess.run(['git','-C',str(repo),'apply',str(path)],check=True)
from check_toolchain import verify
verify()
print('PASS: exact reviewed patches applied')
