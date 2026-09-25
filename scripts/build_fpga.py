#!/usr/bin/env python3
"""Build, but never program, the Tang Primer 20K LED or VGA design."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CFG = runpy.run_path(str(ROOT / "fpga/tang_primer_20k/config.py"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=CFG["TARGETS"])
    args = parser.parse_args()
    subprocess.run([sys.executable, "scripts/check_toolchain.py"], cwd=ROOT, check=True)
    suite = ROOT / "build/fpga_tools/oss-cad-suite"
    if (suite / "VERSION").read_text().strip() != CFG["SUITE_VERSION"]:
        raise SystemExit("Unexpected OSS CAD Suite version")
    target = CFG["TARGETS"][args.target]
    out = ROOT / "build" / ("fpga_" + args.target)
    out.mkdir(parents=True, exist_ok=True)
    commands = [
        [str(suite / "bin/yosys"), "-p",
         "read_verilog " + " ".join(target["sources"]) + "; synth_gowin -top "
         + target["top"] + " -family gw2a -json " + str(out / "synth.json")],
        [str(suite / "bin/nextpnr-himbaechel"), "--json", str(out / "synth.json"),
         "--write", str(out / "pnr.json"), "--device", CFG["DEVICE"],
         "--vopt", "family=" + CFG["FAMILY"], "--vopt", "cst=" + target["cst"],
         "--seed", str(CFG["SEED"]), "--freq", str(CFG["INPUT_MHZ"]),
         "--sdc", target["sdc"],
         "--report", str(out / "timing.json")],
        [str(suite / "bin/gowin_pack"), "-c", "-d", CFG["FAMILY"], *target["pack_options"],
         "-o", str(out / (args.target + ".fs")), str(out / "pnr.json")],
    ]
    (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    for name, command in zip(("synth", "pnr", "pack"), commands):
        print(f"{name}: {out / (name + '.log')}", flush=True)
        with (out / (name + ".log")).open("w") as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    files = target["sources"] + [target["cst"], "fpga/tang_primer_20k/config.py",
        target["sdc"], "scripts/build_fpga.py",
        str((out / (args.target + ".fs")).relative_to(ROOT))]
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files}
    (out / "sha256.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print(out / (args.target + ".fs"))


if __name__ == "__main__":
    main()
