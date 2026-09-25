#!/usr/bin/env python3
"""Verify the self-contained submission manifest; no EDA dependencies."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        p = ROOT / name
        assert p.is_file() and not p.is_symlink(), name
        assert hashlib.sha256(p.read_bytes()).hexdigest() == expected, 'Changed: ' + name
    for line in (ROOT / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    assert manifest['gds_sha256'] == hashlib.sha256((ROOT / 'ishi_vga.gds').read_bytes()).hexdigest()
    assert manifest['frame_integrated'] is False
    print('PASS:', len(manifest['files']), 'manifest files; GDS identity; frame remains unintegrated')
    return manifest


if __name__ == '__main__':
    verify()
