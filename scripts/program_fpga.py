#!/usr/bin/env python3
"""Load a checked Tang Primer 20K bitstream into SRAM and bind its receipt to the data."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', choices=['vga_letter_animation'])
    args = parser.parse_args()
    out = ROOT / 'build' / ('fpga_' + args.target)
    bitstream = out / (args.target + '.fs')
    hashes = json.loads((out / 'sha256.json').read_text())
    assert all(sha(ROOT / name) == digest for name, digest in hashes.items())
    audit = json.loads((out / 'preprogram_verification.json').read_text())
    digest = sha(bitstream)
    assert audit['status'] == 'PASS' and audit['bitstream_sha256'] == digest
    command = ['bash', 'scripts/fpga_loader.sh', '-b', 'tangprimer20k', '-m', str(bitstream)]
    with (out / 'program.log').open('wb') as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    data = (out / 'program.log').read_bytes()
    success = result.returncode == 0 and b'100.00%' in data and b'DONE' in data
    assert sha(bitstream) == digest
    receipt = {'status': 'PASS' if success else 'FAIL', 'mode': 'SRAM',
               'bitstream_sha256': digest, 'program_log_sha256': sha(out / 'program.log'),
               'returncode': result.returncode, 'command': command,
               'script_sha256': sha(Path(__file__))}
    (out / 'programming.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(data.decode(errors='replace'), end='')
    if not success:
        raise SystemExit(result.returncode or 1)


if __name__ == '__main__':
    main()
