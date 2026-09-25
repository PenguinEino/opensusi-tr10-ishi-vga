"""Fail closed on OpenSTA Tcl errors, incomplete reports and electrical violations.

Used only for direct syn/sta/sta.sh calls by run_apr.py. Upstream is untouched.
This is a cell-model check, not interconnect/physical signoff.
"""
import json
from pathlib import Path
import re
import subprocess
import tempfile


def assess(text, expected_registers):
    failures = []
    if re.search(r'^\s*(?:Error|Warning|FATAL)(?:\s|:)', text, re.M | re.I):
        failures.append('tool error or unhandled warning')
    for marker in ('GATE_BEGIN', 'ELECTRICAL_BEGIN', 'ELECTRICAL_END', 'GATE_END'):
        if text.splitlines().count('ISHI_STA_' + marker) != 1:
            failures.append('missing/duplicate ' + marker)
    for field, expected in [('CLOCKS', 1), ('REG_CLOCKS', expected_registers), ('REG_DATA', expected_registers)]:
        values = re.findall(r'^ISHI_STA_' + field + r' (\d+)$', text, re.M)
        if len(values) != 1 or int(values[0]) != expected:
            failures.append(field + ' count mismatch')
    slacks = {}
    for field in ('SETUP', 'HOLD', 'OUTPUT'):
        values = re.findall(r'^ISHI_STA_' + field + r' (-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)$', text, re.M)
        if len(values) != 1:
            failures.append('missing/duplicate ' + field + ' path')
        else:
            slacks[field.lower()] = float(values[0])
            if float(values[0]) < 0:
                failures.append(field + ' violation')
    if re.search(r'\bVIOLATED\b', text):
        failures.append('reported constraint violation')
    return {'status': 'FAIL' if failures else 'PASS', 'failures': failures,
            'expected_registers': expected_registers, 'slack_ns': slacks,
            'scope': 'propagated cell clocks, pin capacitance, no wire RC unless explicitly supplied'}


def run(cmd, cwd, env, upstream, root):
    # cmd = sh, sta.sh, netlist, top, period, [requested report]
    if len(cmd) not in (5, 6):
        raise RuntimeError('STA requires netlist, top, period, and optional report Tcl')
    net = (cwd / cmd[2]).resolve()
    expected = len(re.findall(r'^\s*DFF(?:RB|S)?\s+\\?\S+\s*\(', net.read_text(), re.M))
    if expected == 0:
        raise RuntimeError('No supported v59_4 DFF instances: refusing an empty VGA STA')
    requested = (cwd / cmd[5]).resolve() if len(cmd) == 6 else upstream / 'syn/sta/report.tcl'
    report = requested.read_text() + '\n' + (root / 'scripts/sta_guard.tcl').read_text()
    # The temporary Tcl is a composed caller report, not a copied upstream tool.
    with tempfile.TemporaryDirectory(prefix='ishi_sta_') as temp:
        path = Path(temp) / 'report.tcl'
        path.write_text(report)
        proc = subprocess.run(cmd[:5] + [str(path)], cwd=cwd, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(proc.stdout, end='', flush=True)
    result = assess(proc.stdout, expected)
    if proc.returncode:
        result['status'] = 'FAIL'
        result['failures'].append('upstream exit ' + str(proc.returncode))
    dest = net.parent / ('STA_' + cmd[3] + '.guard.json')
    dest.write_text(json.dumps(result, indent=2) + '\n')
    print('STA guard:', result['status'], '; '.join(result['failures']), flush=True)
    return 0 if result['status'] == 'PASS' else 1
