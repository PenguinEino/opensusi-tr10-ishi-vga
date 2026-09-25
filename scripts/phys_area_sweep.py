#!/usr/bin/env python3
"""Physical-area trials for the architecture handoff netlist.

Every APRtools invocation goes through run_apr.py and writes only to an
experiments/phys_* design root.  The source netlist is immutable input.
"""
import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "experiments/arch_offset_h80/out/ishi_vga_core_pnr.v"

H80 = "experiments/arch_offset_h80"
HV = "experiments/combine_direct_bounds_h80_v500"
DESC = "experiments/descending_h79_v500"
CASES = {
    "A": {"rtl_dir": H80, "netlist": f"{H80}/out/ishi_vga_core_pnr.v", "rows": 7, "tracks": 296, "seed": 4, "restarts": 80,
          "balance": 0.08, "prl": 10},
    "B": {"rtl_dir": H80, "netlist": f"{H80}/out/ishi_vga_core_pnr.v", "rows": 6, "tracks": 296, "seed": 4, "restarts": 80,
          "balance": 0.08, "prl": 10},
    "C": {"rtl_dir": H80, "netlist": f"{H80}/out/ishi_vga_core_pnr.v", "rows": 6, "tracks": 328, "seed": 4, "restarts": 80,
          "balance": 0.08, "prl": 10},
    "D": {"rtl_dir": H80, "netlist": f"{H80}/out/ishi_vga_core_pnr.v", "rows": 6, "tracks": 296, "seed": 4, "restarts": 80,
          "balance": 0.08, "prl": 5},
    "E": {"rtl_dir": H80, "netlist": f"{H80}/out/ishi_vga_core_pnr.v", "rows": 5, "tracks": 328, "seed": 4, "restarts": 160,
          "balance": 0.02, "prl": 10},
    "F": {"rtl_dir": HV, "netlist": f"{HV}/out/ishi_vga_core_pnr.v", "rows": 6, "tracks": 328, "seed": 4, "restarts": 80,
          "balance": 0.08, "prl": 10},
    "G": {"rtl_dir": HV, "netlist": f"{HV}/out/ishi_vga_core_pnr.v", "rows": 5, "tracks": 328, "seed": 4, "restarts": 160,
          "balance": 0.02, "prl": 10},
    "H": {"rtl_dir": H80, "netlist": f"{H80}/out/ishi_vga_core_pnr.v", "rows": 5, "tracks": 328, "seed": 4, "restarts": 800,
          "order_passes": 40, "balance": 0.02, "prl": 10, "compare": "E"},
    "I": {"rtl_dir": H80, "netlist": f"{H80}/out/ishi_vga_core_pnr.v", "rows": 5, "tracks": 328, "seed": 7, "restarts": 160,
          "order_passes": 40, "balance": 0.05, "prl": 10, "compare": "E"},
    "J": {"rtl_dir": DESC, "netlist": f"{DESC}/out/ishi_vga_core_pnr.v", "rows": 5, "tracks": 328, "seed": 4, "restarts": 160,
          "order_passes": 20, "balance": 0.02, "prl": 10},
}


def make(case):
    spec = dict(CASES[case])
    tag = {"F": "hv6", "G": "hv5", "J": "desc5"}.get(case, case.lower())
    name = f"phys_{tag}"
    design = ROOT / "experiments" / name
    design.mkdir(parents=True, exist_ok=True)
    for sub in ("build", "out"):
        (design / sub).mkdir(exist_ok=True)
    source_net = ROOT / spec["netlist"]
    rtl_dir = ROOT / spec["rtl_dir"]
    src_hash = hashlib.sha256(source_net.read_bytes()).hexdigest()
    (design / "out/ishi_vga_core_pnr.v").write_bytes(source_net.read_bytes())
    for rtl_name in ("ishi_vga_core.v", "ishi_logo.v"):
        rtl_file = rtl_dir / rtl_name
        if rtl_file.exists():
            (design / rtl_name).write_bytes(rtl_file.read_bytes())

    # Keep a complete independent design config and set every geometry value
    # before config_base.finalize() derives paths and dimensions.
    cfg = (rtl_dir / "config.py").read_text()
    values = {
        "N_ROWS": str(spec["rows"]),
        "CORE_WIDTH_TRACKS": str(spec["tracks"]),
        "CH_HEIGHTS": "[140.4] + [151.2] * " + str(spec["rows"] - 1) + " + [162.0]",
        "ROUTE_CH_HEIGHTS": "[216.0] + [900.0] * " + str(spec["rows"] - 1) + " + [216.0]",
        "PLACE_SEED": str(spec["seed"]),
        "PLACE_RESTARTS": str(spec["restarts"]),
        "PLACE_ORDER_PASSES": str(spec.get("order_passes", 20)),
        "PAD_WEIGHT": "1.0",
    }
    for key, value in values.items():
        cfg, n = re.subn(r"^" + key + r"\s*=.*$", key + " = " + value, cfg, count=1, flags=re.M)
        if n != 1:
            raise RuntimeError(f"expected one config setting: {key}")
    cfg = cfg.replace(
        "finalize(globals())",
        f"PLACE_BALANCE_TOL = {spec['balance']}\nPLACE_FILL_MODE = 'alternate'\n"
        f"ROUTING_KNOBS = {{'PRL_MIN_PINS': {spec['prl']}, 'SPAN_LANE_PACK': False}}\n"
        "_upstream_getenv = getenv\n"
        "def getenv(name, default=None, cast=None):\n"
        "    if name not in ROUTING_KNOBS:\n"
        "        return _upstream_getenv(name, default, cast)\n"
        "    value = ROUTING_KNOBS[name]\n"
        "    return cast(value) if cast else value\n\n"
        "finalize(globals())",
    )
    (design / "config.py").write_text(cfg)
    spec.update({"case": case, "source": spec["netlist"], "rtl_source": spec["rtl_dir"],
                 "sha256": src_hash, "design": name, "fill": "alternate",
                 "pad_weight": 1.0, "span_lane_pack": False})
    (design / "source_manifest.json").write_text(json.dumps(spec, indent=2) + "\n")
    return design, spec


def run(design, entry, args, logname):
    cmd = ["python3", str(ROOT / "scripts/run_apr.py"), "--design-root",
           str(design.relative_to(ROOT)), entry, *args]
    start = time.time()
    with (design / "build" / logname).open("w") as log:
        rc = subprocess.call(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        log.write(f"\nELAPSED_SECONDS={time.time()-start:.1f}\nRETURN_CODE={rc}\n")
    return rc


def measure(design, spec, do_step7=False):
    report = dict(spec)
    p = design / "layout/step1/place_step1_rows.json"
    if p.exists():
        placement = json.loads(p.read_text())
        report["placement_cut"] = placement.get("cut")
        report["channel_crossings"] = placement.get("channel_crossings")
    p = design / "layout/step4/place_step4_fill.json"
    assignment_hash = None
    if p.exists():
        placed = json.loads(p.read_text())
        assignment = [[(c.get("inst"), c.get("cell"), c.get("x"), c.get("w"))
                       for c in row if c.get("inst")] for row in placed.get("rows", [])]
        assignment_hash = hashlib.sha256(json.dumps(assignment, separators=(",", ":")).encode()).hexdigest()
        report["placement_assignment_sha256"] = assignment_hash
        occ = []
        for row in placed.get("rows", []):
            occ.append(round(sum(float(c.get("w", 0)) for c in row
                                 if c.get("inst") and not c.get("cell", "").startswith(("FILL", "TAP"))), 3))
        report["row_occupied_um"] = occ
        report["max_row_occupied_um"] = max(occ, default=None)
    route_log = (design / "build/route_step6.log").read_text(errors="replace") if (design / "build/route_step6.log").exists() else ""
    m = re.search(r"(\d+) PROBLEM\(S\) FOUND", route_log)
    report["step6_connectivity_problem_reports"] = int(m[1]) if m else (0 if "No connectivity problems" in route_log else None)
    report["step6_simple_drc_counts"] = [s.strip() for s in route_log.splitlines()
                                         if re.search(r"\bviol(?:=|\s)|viol\s*:", s, re.I)]
    report["step6_simple_drc_zero"] = bool(report["step6_simple_drc_counts"]) and all(
        int(n) == 0 for s in report["step6_simple_drc_counts"]
        for n in re.findall(r"(?:viol\s*=|viol\s*:\s*)(\d+)", s, re.I))
    report["step6_short_suspected_warnings"] = len(re.findall(r"SHORT SUSPECTED", route_log))
    comp = (design / "build/diagnostic_compaction.log").read_text(errors="replace") if (design / "build/diagnostic_compaction.log").exists() else ""
    m = re.search(r"コア高 実測 ([\d.]+) um\s+（bbox ([\d.-]+),([\d.-]+) - ([\d.-]+),([\d.-]+)）", comp)
    if m:
        report["bbox_um"] = [float(m[2]), float(m[3]), float(m[4]), float(m[5])]
        report["bbox_width_um"] = round(float(m[4]) - float(m[2]), 3)
        report["bbox_height_um"] = float(m[1])
    if do_step7:
        rc = run(design, "apr/route.py", ["--from", "7", "--to", "7"], "route_step7.log")
        report["step7_return_code"] = rc
        step7text = (design / "build/route_step7.log").read_text(errors="replace")
        matches = re.findall(r"(\d+) PROBLEM\(S\) FOUND", step7text)
        report["step7_connectivity_problem_reports"] = int(matches[-1]) if matches else (0 if "No connectivity problems" in step7text else None)
    (design / "build/physical_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case", choices=["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"])
    ap.add_argument("--step7", action="store_true")
    a = ap.parse_args()
    design, spec = make(a.case)
    if run(design, "apr/place.py", [], "place.log"):
        measure(design, spec)
        raise SystemExit("placement failed; see build/place.log")
    run(design, "apr/verify_placement.py", [], "verify_placement.log")
    pre = measure(design, spec)
    compare = spec.get("compare")
    if compare:
        compare_report = ROOT / "experiments" / f"phys_{compare.lower()}" / "build/physical_report.json"
        compare_design = ROOT / "experiments" / f"phys_{compare.lower()}"
        old = json.loads(compare_report.read_text())
        old_hash = old.get("placement_assignment_sha256")
        if old_hash is None:
            old_place = json.loads((compare_design / "layout/step4/place_step4_fill.json").read_text())
            old_assignment = [[(c.get("inst"), c.get("cell"), c.get("x"), c.get("w"))
                               for c in row if c.get("inst")] for row in old_place.get("rows", [])]
            old_hash = hashlib.sha256(json.dumps(old_assignment, separators=(",", ":")).encode()).hexdigest()
        if pre.get("placement_assignment_sha256") == old_hash:
            pre["route_skipped_identical_assignment_to"] = f"phys_{compare.lower()}"
            (design / "build/physical_report.json").write_text(json.dumps(pre, indent=2, ensure_ascii=False) + "\n")
            print(json.dumps(pre, ensure_ascii=False, indent=2))
            return
    if run(design, "apr/route.py", ["--to", "6"], "route_step6.log"):
        measure(design, spec)
        raise SystemExit("step6 routing failed; see build/route_step6.log")
    squeeze_args = ["--in-gds", "layout/step6/route_step_2_routed_raw.gds", "-o",
                    "build/diagnostic_compacted.gds", "--pin-map-in", "layout/pin_map.json",
                    "--pin-map-out", "build/diagnostic_pins.json", "--net-shapes-in",
                    "layout/net_shapes.json", "--net-shapes-out", "build/diagnostic_shapes.json"]
    run(design, "apr/squeeze_channels.py", squeeze_args, "diagnostic_compaction.log")
    report = measure(design, spec, a.step7)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
