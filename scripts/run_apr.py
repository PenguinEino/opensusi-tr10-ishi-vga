#!/usr/bin/env python3
"""Run a pinned upstream entry point after provenance checks.
Example: python3 scripts/run_apr.py apr/check_ledger.py
Isolated experiment: python3 scripts/run_apr.py --design-root experiments/row_patterns syn/syn.sh
"""
import os
from pathlib import Path
import subprocess
import sys
from check_toolchain import ROOT, verify

def main():
    verify()
    args = sys.argv[1:]
    design = ROOT
    if args[:1] == ['--design-root']:
        if len(args) < 3:
            raise RuntimeError('--design-root requires a directory and an APRtools entry point')
        design = (ROOT / args[1]).resolve()
        if not design.is_relative_to(ROOT):
            raise RuntimeError('Experiment must be inside this workspace')
        args = args[2:]
    if not args:
        raise RuntimeError('Specify an APRtools entry point, e.g. apr/check_ledger.py')
    upstream = ROOT / 'tools/APRtools'
    requested = Path(args[0])
    target = (upstream / requested).resolve()
    if (requested.is_absolute() or '..' in requested.parts or
            requested.parts[0] not in ('apr', 'syn', 'char') or
            not target.is_relative_to(upstream.resolve()) or not target.is_file()):
        raise RuntimeError('Only pinned apr/, syn/, char/ entry points are allowed')
    if target.suffix not in ('.py', '.sh'):
        raise RuntimeError('Entry point must be .py or .sh')
    independent = {'apr/check_ledger.py', 'apr/check_copies.py',
                   'apr/check_no_home_paths.py', 'apr/lint.py'}
    if str(requested) not in independent and not (design / 'config.py').is_file():
        raise RuntimeError('Design config.py is not ready; refusing upstream design defaults')
    env = dict(os.environ)
    env.update(APRTOOLS=str(upstream), TR1UM_PDK=str(ROOT / 'tools/TR-1um'),
               PYTHONPATH=str(upstream / 'apr'), PYTHONHASHSEED='0', PYTHONNOUSERSITE='1')
    python = ROOT / '.venv/bin/python'
    if not python.exists():
        raise RuntimeError('Run scripts/setup_python.sh first (local KLayout environment required)')
    env['PATH'] = os.pathsep.join([str(ROOT / '.tools/bin'), str(python.parent), env['PATH']])
    env['PYTHONUNBUFFERED'] = '1'
    env['LD_LIBRARY_PATH'] = str(ROOT / '.tools/root/usr/lib/aarch64-linux-gnu') + os.pathsep + env.get('LD_LIBRARY_PATH', '')
    cmd = [str(python) if target.suffix == '.py' else 'sh', str(target), *args[1:]]
    if str(requested) == 'syn/sta/sta.sh':
        from sta_guard import run
        return run(cmd, design, env, upstream, ROOT)
    return subprocess.call(cmd, cwd=design, env=env)

if __name__ == '__main__':
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
