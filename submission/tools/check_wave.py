#!/usr/bin/env python3
"""Design-owned portable checker for saved or newly generated ngspice waves.

Checks the same state/output contract as scripts/power_spice_check.py, without
depending on the original workspace paths or APRtools Python imports.
"""
import gzip
import re
from pathlib import Path
import numpy as np


def check(path, case, expected_path):
    path = Path(path)
    binary = gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()
    head, body = binary.split(b'Binary:\n', 1)
    header = head.decode()
    assert 'Flags: real' in header and 'Plotname: Transient Analysis' in header
    count = int(re.search(r'No\. Variables:\s*(\d+)', header)[1])
    points = int(re.search(r'No\. Points:\s*(\d+)', header)[1])
    names = {m[2].lower(): int(m[1]) for m in re.finditer(
        r'^\s*(\d+)\s+(\S+)\s+\S+\s*$', header.split('Variables:\n')[1], re.M)}
    data = np.frombuffer(body, dtype=np.float64).reshape(points, count)
    time_s = data[:, 0]
    assert np.isfinite(data).all() and np.all(np.diff(time_s) > 0)
    times = (case['delay_ns'] + np.arange(case['ticks']) * case['period_ns'] + 150) * 1e-9
    assert time_s[-1] >= times[-1], 'Incomplete transient'
    values = np.array([np.interp(times, time_s, data[:, names['v(' + s.lower() + ')']])
                       for s in case['signals']]).T
    bits = np.where(values < 1.5, 0, np.where(values > 3.5, 1, -1))
    first = 32 if case['natural'] else 0
    assert not (bits[first:] < 0).any(), 'Undefined voltage at sample'
    h = bits[:, 6:13] @ (2 ** np.arange(7))
    v = bits[:, 13:23] @ (2 ** np.arange(10))
    outputs = bits[:, 1:6] @ np.array([4, 2, 1, 8, 16])
    expected = np.array([int(x, 16) for x in Path(expected_path).read_text().split()])
    assert len(expected) == 52500
    state_reference=None
    if case.get('binary_state_reference'):
        state_reference=np.array([int(x,16) for x in (Path(expected_path).parent/case['binary_state_reference']).read_text().split()])
        assert len(state_reference)==131072
    raster_checked=0
    ph, pv = (int(h[first - 1]), int(v[first - 1])) if first else (case['h'], case['v'])
    checked = 0
    for i in range(first, case['ticks']):
        nh, nv = ((71, 500 if pv == 0 else (pv + 1) % 1024)
                  if ph == 100 else ((ph - 1) % 128, pv))
        assert (int(h[i]), int(v[i])) == (nh, nv), ('counter', i, h[i], v[i], nh, nv)
        x, y = (71 - ph) % 128, (pv - 500) % 1024
        in_raster=x<100 and y<525
        raster_checked+=int(in_raster)
        assert in_raster or state_reference is not None, ('outside specified raster', i, x, y)
        ref=state_reference[(pv<<7)|ph] if state_reference is not None else expected[y*100+x]
        assert outputs[i] == ref, ('output', i, outputs[i], ref)
        checked += 1
        ph, pv = int(h[i]), int(v[i])
    assert checked == case['ticks'] - first
    return {'status': 'PASS', 'cycles_checked': checked, 'counter_bits': 17, 'output_bits': 5,
            'raster_cycles_checked': raster_checked,
            'scope': 'selected transient window; no wire RC', 'sample_offset_ns': 150}
