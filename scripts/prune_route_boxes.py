#!/usr/bin/env python3
"""Prune only exact top-level route rectangles when connectivity improves.

The frozen source is never rewritten. Every accepted deletion must strictly
reduce the set of unintended actual-pin short pairs, preserve the source's
opens/missing-pin/power invariants, and pass official drawing DRC as a marker
subset of the immediately preceding accepted layout.
"""
from __future__ import annotations
from collections import defaultdict
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/box_prune"))
sys.path.insert(0, str(ROOT / "tools/APRtools/apr"))
import klayout.db as db
import lef_parser
import rules
from check_toolchain import verify
_cfg_spec = importlib.util.spec_from_file_location("box_prune_config", ROOT / "experiments/box_prune/config.py")
cfg = importlib.util.module_from_spec(_cfg_spec)
_cfg_spec.loader.exec_module(cfg)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def helper():
    spec = importlib.util.spec_from_file_location("via_prune_helpers", ROOT / "scripts/prune_route_vias.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pin_layer_map(placement_path: Path):
    lef = lef_parser.parse_lef(ROOT / "tools/APRtools/stdcell/v59_4/TR-1um_cells.lef")
    placement = json.loads(placement_path.read_text())
    layers = {}
    for row in placement["rows"]:
        for inst in row:
            for pin, entry in lef[inst["type"]]["pins"].items():
                metal = [{"METAL1": "M1", "METAL2": "M2"}[rect[0]]
                         for rect in entry["rects"] if rect[0] in ("METAL1", "METAL2")]
                if metal:
                    layers[(inst["name"], pin)] = metal[0]
    return layers


def dbox_um(rect, dbu):
    return db.Box(*(int(round(float(v) / dbu)) for v in rect))


def box_um(box, dbu):
    return tuple(round(v * dbu, 4) for v in (box.left, box.bottom, box.right, box.top))


def run_drc(gds: Path, report: Path, design_root: Path):
    report.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/run_apr.py"),
                           "--design-root", str(design_root), "apr/drc_pdk.py",
                           str(gds), cfg.BOX_PRUNE["top"], "-r", str(report)],
                          text=True, capture_output=True)
    log = report.with_suffix(".log")
    log.write_text(proc.stdout + proc.stderr)
    if proc.returncode not in (0, 1) or not report.is_file():
        raise RuntimeError(f"official DRC failed: exit={proc.returncode}; see {log}")
    return helper().markers(report)


def pin_xy_by_net(pins):
    return {net: [(float(p[2]), float(p[3])) for p in entries]
            for net, entries in pins.items()}


def close_to_box(x, y, rect, threshold):
    x0, y0, x1, y1 = rect
    dx = max(x0 - x, 0.0, x - x1)
    dy = max(y0 - y, 0.0, y - y1)
    return dx * dx + dy * dy <= threshold * threshold


def candidate_groups(top, layout, shape_map, current_pairs, pins, cfgvals, removed):
    by_box = defaultdict(list)
    for tag, (layer, datatype) in (("M1", rules.M1), ("M2", rules.M2)):
        idx = layout.layer(layer, datatype)
        for shape in top.shapes(idx).each():
            if shape.is_box():
                by_box[(tag, tuple(shape.box.to_s().split()))].append(shape)

    # Canonical geometry keys are exact DBU tuples.
    shape_groups = {}
    for (tag, _), shapes in by_box.items():
        b = shapes[0].box
        key = (tag, (b.left, b.bottom, b.right, b.top))
        shape_groups[key] = shapes

    recs = []
    claims = defaultdict(set)
    for net, entries in shape_map.items():
        for i, entry in enumerate(entries):
            if len(entry) != 5 or entry[0] not in ("M1", "M2"):
                continue
            tag = entry[0]
            rect = tuple(float(v) for v in entry[1:])
            key = (tag, tuple(dbox_um(rect, layout.dbu).to_s().split()))
            # The string key above mirrors KLayout's exact box serialization;
            # also maintain numeric lookup for robust ownership matching.
            numeric = (tag, tuple((dbox_um(rect, layout.dbu).left,
                                   dbox_um(rect, layout.dbu).bottom,
                                   dbox_um(rect, layout.dbu).right,
                                   dbox_um(rect, layout.dbu).top)))
            claims[numeric].add(net)
            recs.append((net, i, tag, rect, numeric))

    map_overlaps = set()
    tol = cfgvals["touch_tolerance_um"]
    for i, a in enumerate(recs):
        for b in recs[i + 1:]:
            if a[0] == b[0] or a[2] != b[2]:
                continue
            A, B = a[3], b[3]
            if (max(A[0], B[0]) <= min(A[2], B[2]) + tol and
                max(A[1], B[1]) <= min(A[3], B[3]) + tol):
                pair = tuple(sorted((a[0], b[0])))
                if pair in current_pairs:
                    map_overlaps.add((a[4], pair))
                    map_overlaps.add((b[4], pair))

    pin_coords = pin_xy_by_net(pins)
    candidate_reasons = defaultdict(set)
    for key, pair in map_overlaps:
        candidate_reasons[key].add("same_layer_map_overlap:" + "/".join(pair))
    for net, _, _, rect, key in recs:
        for pair in current_pairs:
            if net not in pair:
                continue
            if any(close_to_box(x, y, rect, cfgvals["near_pin_um"])
                   for x, y in pin_coords.get(net, [])):
                candidate_reasons[key].add("near_short_pair_pin")

    candidates = []
    for key, reasons in candidate_reasons.items():
        if key in removed:
            continue
        tag, box = key
        shapes = shape_groups.get(key)
        if not shapes:
            continue  # no exact top-level box owner, never approximate-delete
        map_owners = sorted(claims.get(key, ()))
        candidates.append({"key": key, "shapes": list(shapes), "layer": tag,
                           "box_dbu": box, "box_um": list(box_um(shapes[0].box, layout.dbu)),
                           "map_owners": map_owners, "reasons": sorted(reasons)})
    candidates.sort(key=lambda x: (x["layer"], x["box_dbu"]))
    return candidates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight-only", action="store_true",
                    help="inventory exact candidate boxes without DRC or GDS writes")
    args = ap.parse_args()
    verify()
    st = cfg.BOX_PRUNE
    exp = ROOT / "experiments/box_prune"
    build = exp / "build"
    build.mkdir(parents=True, exist_ok=True)
    source = ROOT / st["source_gds"]
    expected = st["source_sha256"]
    if sha(source) != expected:
        raise RuntimeError(f"frozen source hash mismatch: {sha(source)} != {expected}")
    pins = json.loads((ROOT / st["actual_pins"]).read_text())
    shapes_map = json.loads((ROOT / st["shapes"]).read_text())
    pin_layers = pin_layer_map(ROOT / st["placement"])
    h = helper()
    ly = db.Layout(); ly.read(str(source))
    top = ly.cell(st["top"])
    if top is None: raise RuntimeError(f"missing top cell {st['top']}")
    current = h.connectivity(ly, top, pins, pin_layers)
    if current["missing"] or current["opens"]:
        raise RuntimeError(f"source does not meet pin/open baseline: {current['missing']} / {current['opens']}")
    if len(current["pairs"]) != st["expected_source_pairs"]:
        raise RuntimeError(f"source pair count changed: {len(current['pairs'])} != {st['expected_source_pairs']}")
    if args.preflight_only:
        candidates = candidate_groups(top, ly, shapes_map, current["pairs"], pins, st, set())
        summary = {"status": "PREFLIGHT_ONLY", "source_gds": st["source_gds"],
                   "source_sha256": sha(source), "pair_count": len(current["pairs"]),
                   "opens": current["opens"], "missing": current["missing"],
                   "power_component_counts": current["power_component_counts"],
                   "rail_signal_nets": current["rail_signal_nets"],
                   "candidate_count": len(candidates),
                   "candidates": [{k: v for k, v in c.items() if k != "shapes"} for c in candidates]}
        path = build / "candidates.json"
        path.write_text(json.dumps(summary, indent=2) + "\n")
        print(f"Preflight only: {len(candidates)} exact-box candidates; no DRC/GDS writes")
        return
    source_drc_path = ROOT / st["source_drc"]
    if not source_drc_path.exists():
        source_markers = run_drc(source, source_drc_path, ROOT / "experiments/via_prune")
    else:
        source_markers = h.markers(source_drc_path)
    current_markers = set(source_markers)
    initial_pair_count = len(current["pairs"])
    invariants = {k: current[k] for k in ("power_component_counts", "rail_signal_nets")}
    removed = set(); accepted = []; trials = []

    for pass_no in range(st["max_passes"]):
        candidates = candidate_groups(top, ly, shapes_map, current["pairs"], pins, st, removed)
        print(f"Pass {pass_no}: {len(candidates)} exact-box candidates; {len(current['pairs'])} short pairs", flush=True)
        pass_accepted = 0
        for ci, cand in enumerate(candidates):
            key = cand["key"]
            live = [s for s in top.shapes(ly.layer(*getattr(rules, cand["layer"]))).each()
                    if s.is_box() and (s.box.left, s.box.bottom, s.box.right, s.box.top) == key[1]]
            if not live:
                removed.add(key); continue
            for s in live: s.delete()
            trial = h.connectivity(ly, top, pins, pin_layers)
            good_connectivity = (not trial["missing"] and not trial["opens"] and
                                 trial["pairs"] < current["pairs"] and
                                 trial["power_component_counts"] == invariants["power_component_counts"] and
                                 trial["rail_signal_nets"] == invariants["rail_signal_nets"])
            rec = {"pass": pass_no, "index": ci, "layer": cand["layer"],
                   "box_um": cand["box_um"], "removed_exact_shape_count": len(live),
                   "map_owners": cand["map_owners"], "reasons": cand["reasons"],
                   "before_pair_count": len(current["pairs"]),
                   "after_pair_count": len(trial["pairs"]),
                   "opens": trial["opens"], "missing": trial["missing"],
                   "power_unchanged": trial["power_component_counts"] == invariants["power_component_counts"] and trial["rail_signal_nets"] == invariants["rail_signal_nets"],
                   "strict_pair_subset": trial["pairs"] < current["pairs"], "accepted": False}
            if good_connectivity:
                folder = build / f"trial_{len(trials):04d}"
                folder.mkdir(parents=True, exist_ok=True)
                candidate_gds = folder / "candidate.gds"
                marker_path = folder / "drawing.lyrdb"
                ly.write(str(candidate_gds))
                # Use the accepted APR design configuration while keeping all
                # generated DRC artifacts in this experiment's own build dir.
                markers = run_drc(candidate_gds, marker_path, ROOT / "experiments/via_prune")
                new_markers = markers - current_markers
                rec.update({"candidate_gds": str(candidate_gds.relative_to(ROOT)),
                            "candidate_sha256": sha(candidate_gds),
                            "drc_marker_count": len(markers),
                            "new_drc_marker_count": len(new_markers)})
                if not new_markers:
                    rec["accepted"] = True
                    rec["resolved_pairs"] = sorted(map(list, current["pairs"] - trial["pairs"]))
                    current = trial; current_markers = markers
                    removed.add(key); accepted.append(rec); pass_accepted += 1
                    print(f"  accepted {cand['layer']} {cand['box_um']}: {len(current['pairs'])} pairs", flush=True)
                else:
                    rec["new_drc_markers"] = sorted([list(m) for m in new_markers])
            trials.append(rec)
            if not rec["accepted"]:
                # Restore the exact group boxes. Shape properties are not needed
                # for these unannotated APR route rectangles.
                idx = ly.layer(*getattr(rules, cand["layer"]))
                for _ in live: top.shapes(idx).insert(db.Box(*key[1]))
        if pass_accepted == 0: break

    final_gds = build / "box_pruned.gds"
    if accepted:
        ly.write(str(final_gds))
    else:
        shutil.copyfile(source, final_gds)
    final_conn = h.connectivity(ly, top, pins, pin_layers)
    assert final_conn["pairs"] <= current["pairs"] and not final_conn["opens"] and not final_conn["missing"]
    assert final_conn["power_component_counts"] == invariants["power_component_counts"]
    assert final_conn["rail_signal_nets"] == invariants["rail_signal_nets"]
    assert sha(source) == expected, "source input changed during pruning"
    if not accepted:
        assert sha(final_gds) == expected, "no-op output must be byte-identical to source"
    report = {"status": "COMPLETE", "source_gds": st["source_gds"],
              "source_sha256": sha(source), "source_drc_markers": len(source_markers),
              "final_gds": str(final_gds.relative_to(ROOT)), "final_sha256": sha(final_gds),
              "generator_sha256": sha(Path(__file__)), "config_sha256": sha(exp / "config.py"),
              "before_pair_count": initial_pair_count, "after_pair_count": len(final_conn["pairs"]),
              "before": {"pair_count": initial_pair_count, "power_component_counts": invariants["power_component_counts"],
                         "rail_signal_nets": invariants["rail_signal_nets"]},
              "after": {"pair_count": len(final_conn["pairs"]), "opens": final_conn["opens"],
                        "missing": final_conn["missing"], "power_component_counts": final_conn["power_component_counts"],
                        "rail_signal_nets": final_conn["rail_signal_nets"]},
              "accepted": accepted, "trials": trials}
    (build / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Finished: {len(accepted)} boxes accepted; {len(final_conn['pairs'])} pairs remain", flush=True)


if __name__ == "__main__": main()
