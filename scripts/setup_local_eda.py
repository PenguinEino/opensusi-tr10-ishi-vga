#!/usr/bin/env python3
"""Install Ubuntu arm64 EDA packages into .tools, without sudo/system changes."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'.tools'
for p in ['debs','root','bin']: (base/p).mkdir(parents=True,exist_ok=True)
packages=['yosys=0.33-5build2','yosys-abc=0.33-5build2','iverilog=12.0-2build2',
          'libqhull-dev=2020.2-6build1','libqhull-r8.0=2020.2-6build1']
subprocess.run(['apt-get','download',*packages],cwd=base/'debs',check=True)
for p in (base/'debs').glob('*.deb'):
    subprocess.run(['dpkg-deb','-x',str(p),str(base/'root')],check=True)
for name in ['yosys','yosys-abc','iverilog','vvp']:
    extra=' -B"$HERE/../root/usr/lib/aarch64-linux-gnu/ivl"' if name=='iverilog' else ''
    p=base/'bin'/name
    p.write_text('#!/bin/sh\nHERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
                 f'exec "$HERE/../root/usr/bin/{name}"{extra} "$@"\n')
    p.chmod(0o755)
print('Local EDA ready:',base/'bin')
