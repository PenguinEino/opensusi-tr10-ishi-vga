#!/usr/bin/env python3
"""Validate one maze-route GDS against a frozen, fully audited source.

The design's literal MAZE_ROUTE dictionary is parsed without importing its
config.py. The validator only writes reports beneath that design's build/.
"""
from __future__ import annotations
import argparse
import ast
from collections import defaultdict
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/APRtools/apr"))
import klayout.db as db
import lef_parser
import rules
from check_toolchain import verify


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_literal_config(path: Path):
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "MAZE_ROUTE" for t in node.targets):
            value = ast.literal_eval(node.value)
            if not isinstance(value, dict):
                raise ValueError("MAZE_ROUTE must be a literal dictionary")
            return value
    raise ValueError(f"No literal MAZE_ROUTE assignment in {path}")


def load_helper():
    path = ROOT / "scripts/prune_route_vias.py"
    spec = importlib.util.spec_from_file_location("route_via_connectivity_helpers", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pin_layer_map(placement_path: Path):
    lef = lef_parser.parse_lef(ROOT / "tools/APRtools/stdcell/v59_4/TR-1um_cells.lef")
    place = json.loads(placement_path.read_text())
    mapping = {}
    for row in place["rows"]:
        for inst in row:
            for pin, entry in lef[inst["type"]]["pins"].items():
                metal = [{"METAL1": "M1", "METAL2": "M2"}[r[0]]
                         for r in entry["rects"] if r[0] in ("METAL1", "METAL2")]
                if metal:
                    mapping[(inst["name"], pin)] = metal[0]
    return mapping, place, lef


def route_diagnostics(gds: Path, pins: Path, shapes: Path, placement: Path,
                      out: Path, exp_root: Path):
    out.mkdir(parents=True, exist_ok=True)
    py = ROOT / ".venv/bin/python"
    if not py.is_file():
        raise RuntimeError("pinned Python environment missing; run scripts/setup_python.sh")
    cmd = [str(py), str(ROOT / "scripts/routing_diagnostics.py"),
           "--gds", str(gds), "--pins", str(pins), "--shapes", str(shapes),
           "--placement", str(placement), "--out", str(out), "--poly"]
    proc = subprocess.run(cmd, cwd=exp_root, text=True, capture_output=True)
    (out / "console.log").write_text(proc.stdout + proc.stderr)
    report = out / "metal_connectivity.json"
    if proc.returncode != 0 or not report.is_file():
        raise RuntimeError(f"actual pin-shape audit failed; see {out/'console.log'}")
    return json.loads(report.read_text())


def pairset_from_audit(report):
    pairs = set()
    for group in report["actual_short_components"]:
        nets = sorted(set(group["nets"]))
        pairs.update(tuple(x) for x in itertools.combinations(nets, 2))
    return pairs


def report_markers(path: Path):
    root = ET.parse(path).getroot()
    markers = set()
    for item in root.iter("item"):
        category = item.findtext("category")
        values = tuple(sorted(v.text.strip() for v in item.findall("./values/value") if v.text and v.text.strip()))
        if not category or not values:
            raise ValueError(f"DRC marker lacks category/value at {path}")
        markers.add((category.strip(), values))
    return markers


def run_drc(gds: Path, report: Path, log: Path, exp_root: Path, top: str,
            mdp_gds: Path):
    report.parent.mkdir(parents=True, exist_ok=True)
    mdp_report = gds.with_suffix("").with_name(gds.stem + "_mdp.lyrdb")
    for stale in (report, log, mdp_gds, mdp_report):
        stale.unlink(missing_ok=True)
    cmd = [sys.executable, str(ROOT / "scripts/run_apr.py"),
           "--design-root", str(exp_root.relative_to(ROOT)), "apr/drc_pdk.py",
           str(gds), top, "-r", str(report)]
    cmd += ["--mdp", "--mdp-gds", str(mdp_gds)]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    log.write_text(proc.stdout + proc.stderr)
    if proc.returncode not in (0, 1) or not report.is_file() or not mdp_report.is_file() or not mdp_gds.is_file() or mdp_gds.stat().st_size < 1024:
        raise RuntimeError(f"official drawing/mask DRC did not produce fresh reports; see {log}")
    # Existing known rule markers produce return code 1. The official report
    # and its human-readable violation summary are the result in that case.
    combined = proc.stdout + proc.stderr
    if "DRC:" not in combined and "違反" not in combined:
        raise RuntimeError(f"DRC wrapper log lacks its report summary; see {log}")
    if "MDP:" not in combined or "run_IP62" not in combined:
        raise RuntimeError(f"mask DRC log lacks the official MDP/MDP-check summary; see {log}")
    drawing_markers = report_markers(report)
    mdp_markers = report_markers(mdp_report)
    return drawing_markers, mdp_markers, mdp_gds, mdp_report


def bbox_signature(top):
    b = top.dbbox()
    return tuple(round(float(v), 4) for v in (b.left, b.bottom, b.right, b.top))


def inst_signature(top):
    rows = []
    for inst in top.each_inst():
        if inst.cell.name.lower().startswith("via_"):
            continue
        rows.append((inst.cell.name, inst.trans.to_s(), inst.na, inst.nb,
                     inst.a.x, inst.a.y, inst.b.x, inst.b.y))
    return sorted(rows)


def non_top_cell_inventory(layout, top_name):
    """Fingerprint every non-top cell's raw layer shapes and child instances."""
    inventory = {}
    for cell in layout.each_cell():
        if cell.name == top_name:
            continue
        shapes = []
        for info in layout.layer_infos():
            idx = layout.layer(info)
            for shape in cell.shapes(idx).each():
                shapes.append((info.layer, info.datatype, shape.to_s()))
        children = []
        for inst in cell.each_inst():
            children.append((inst.cell.name, inst.trans.to_s(), inst.na, inst.nb,
                             inst.a.x, inst.a.y, inst.b.x, inst.b.y))
        inventory[cell.name] = {"shapes": tuple(sorted(shapes)),
                                "children": tuple(sorted(children))}
    return inventory


def region_map(layout, top):
    out = {}
    for info in layout.layer_infos():
        key = (info.layer, info.datatype)
        out[key] = db.Region(top.begin_shapes_rec(layout.layer(info))).merged()
    return out


def geometry_diff(source_ly, source_top, candidate_ly, candidate_top):
    src, cand = region_map(source_ly, source_top), region_map(candidate_ly, candidate_top)
    changed = []
    for key in sorted(src.keys() | cand.keys()):
        delta = src.get(key, db.Region()) ^ cand.get(key, db.Region())
        if not delta.is_empty():
            changed.append(key)
    allowed = {rules.M1, rules.M2, rules.V1}
    unexpected = [ld for ld in changed if ld not in allowed]
    return changed, unexpected


def rel_input(exp_root: Path, value: str):
    p = (ROOT / value).resolve()
    if not p.is_relative_to(ROOT):
        raise ValueError(f"MAZE_ROUTE input escapes workspace: {value}")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design-root", required=True, help="experiment directory containing config.py and build/candidate.gds")
    args = ap.parse_args()
    verify()
    exp = (ROOT / args.design_root).resolve()
    if not exp.is_relative_to(ROOT) or not (exp / "config.py").is_file():
        raise ValueError("--design-root must be a workspace experiment with config.py")
    st = read_literal_config(exp / "config.py")
    required = ("source_gds", "source_sha256", "actual_pins", "placement", "shapes")
    missing_keys = [k for k in required if k not in st]
    if missing_keys:
        raise ValueError(f"MAZE_ROUTE missing keys: {missing_keys}")
    top_name = st.get("top", "ishi_vga_core")
    build = exp / "build"
    build.mkdir(parents=True, exist_ok=True)
    source = rel_input(exp, st["source_gds"])
    pins_path = rel_input(exp, st["actual_pins"])
    placement_path = rel_input(exp, st["placement"])
    shapes_path = rel_input(exp, st["shapes"])
    candidate = build / "candidate.gds"
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    if sha256(source) != st["source_sha256"]:
        raise RuntimeError(f"frozen source hash mismatch: {sha256(source)} != {st['source_sha256']}")

    results = {"checks": {}, "errors": []}
    input_paths = {"source_gds": source, "actual_pins": pins_path,
                   "placement": placement_path, "shapes": shapes_path,
                   "config": exp / "config.py", "validator": Path(__file__),
                   "routing_diagnostics": ROOT / "scripts/routing_diagnostics.py",
                   "via_connectivity_helper": ROOT / "scripts/prune_route_vias.py",
                   "toolchain_lock": ROOT / "toolchain.lock.json",
                   "toolchain_check": ROOT / "scripts/check_toolchain.py",
                   "apr_wrapper": ROOT / "scripts/run_apr.py",
                   "pinned_rules": ROOT / "tools/APRtools/apr/rules.py",
                   "pinned_cell_lef": ROOT / "tools/APRtools/stdcell/v59_4/TR-1um_cells.lef",
                   "pinned_drc_script": ROOT / "tools/APRtools/apr/drc_pdk.py",
                   "pdk_drawing_deck": ROOT / "tools/TR-1um/libs.tech/klayout/tech/drc/run.drc",
                   "pdk_mdp_deck": ROOT / "tools/TR-1um/libs.tech/klayout/tech/drc/run_mdp.drc",
                   "pdk_mask_deck": ROOT / "tools/TR-1um/libs.tech/klayout/tech/drc/run_IP62.drc"}
    manifest_path = exp / "build/manifest.json"
    if manifest_path.is_file():
        input_paths["candidate_manifest"] = manifest_path
    hashes = {k: sha256(v) for k, v in input_paths.items()}
    hashes["candidate_gds"] = sha256(candidate)
    initial_candidate_sha = hashes["candidate_gds"]
    helpers = load_helper()
    pin_layers, place, _lef = pin_layer_map(placement_path)

    # Full actual-pin/LEF geometry audit on both source and candidate.
    src_audit_dir, cand_audit_dir = build / "source_audit", build / "audit"
    source_audit = route_diagnostics(source, pins_path, shapes_path, placement_path, src_audit_dir, exp)
    candidate_audit = route_diagnostics(candidate, pins_path, shapes_path, placement_path, cand_audit_dir, exp)
    source_pairs = pairset_from_audit(source_audit)
    candidate_pairs = pairset_from_audit(candidate_audit)
    source_pin_metrics = {k: source_audit[k] for k in
                          ("placement_instances_matched_to_actual_gds", "actual_pin_shapes_labeled",
                           "placement_signal_pin_count", "missing_actual_pin_count", "open_net_count",
                           "placement_instances_missing_from_gds")}
    candidate_pin_metrics = {k: candidate_audit[k] for k in
                             ("placement_instances_matched_to_actual_gds", "actual_pin_shapes_labeled",
                              "placement_signal_pin_count", "missing_actual_pin_count", "open_net_count",
                              "placement_instances_missing_from_gds")}
    counts_ok = (candidate_pin_metrics == source_pin_metrics and
                 candidate_pin_metrics["placement_instances_matched_to_actual_gds"] == 421 and
                 candidate_pin_metrics["actual_pin_shapes_labeled"] == 987 and
                 candidate_pin_metrics["placement_signal_pin_count"] == 987 and
                 candidate_pin_metrics["missing_actual_pin_count"] == 0 and
                 candidate_pin_metrics["open_net_count"] == 0)
    pair_ok = candidate_pairs < source_pairs
    results["checks"]["actual_pin_audit_counts"] = counts_ok
    results["checks"]["short_pairs_strict_subset"] = pair_ok
    if not counts_ok: results["errors"].append("actual pin/instance counts, missing pins, or opens differ from required source baseline")
    if not pair_ok: results["errors"].append("candidate short-pair set is not a strict subset of source")

    # Independent point-extraction connectivity + source-matched rail topology.
    power_results = {}
    for name, gds in (("source", source), ("candidate", candidate)):
        ly = db.Layout(); ly.read(str(gds)); top = ly.cell(top_name)
        if top is None: raise RuntimeError(f"{name} GDS lacks top cell {top_name}")
        power_results[name] = helpers.connectivity(ly, top, json.loads(pins_path.read_text()), pin_layers)
    sconn, cconn = power_results["source"], power_results["candidate"]
    flat_pairs_ok = cconn["pairs"] < sconn["pairs"]
    flat_clean = not cconn["missing"] and not cconn["opens"]
    rails_ok = (cconn["power_component_counts"] == sconn["power_component_counts"] and
                cconn["rail_signal_nets"] == sconn["rail_signal_nets"])
    audit_flat_consistent = source_pairs == sconn["pairs"] and candidate_pairs == cconn["pairs"]
    results["checks"].update({"flat_pairset_strict_subset": flat_pairs_ok,
                              "flat_no_opens_or_missing": flat_clean,
                              "power_topology_unchanged": rails_ok,
                              "audit_and_flat_pairsets_agree": audit_flat_consistent})
    if not flat_pairs_ok: results["errors"].append("flat connectivity pairset is not a strict subset")
    if not flat_clean: results["errors"].append("flat connectivity reports missing pins or open nets")
    if not rails_ok: results["errors"].append("VDD/VSS component counts or attached signal labels changed")
    if not audit_flat_consistent: results["errors"].append("pin-shape audit and flat connectivity pairsets disagree")

    # Geometry scope: fixed bbox and hierarchy; only top routing layers may change.
    source_ly = db.Layout(); source_ly.read(str(source)); source_top = source_ly.cell(top_name)
    cand_ly = db.Layout(); cand_ly.read(str(candidate)); cand_top = cand_ly.cell(top_name)
    bbox_ok = source_ly.dbu == cand_ly.dbu and bbox_signature(source_top) == bbox_signature(cand_top)
    hierarchy_ok = inst_signature(source_top) == inst_signature(cand_top)
    source_cell_inventory = non_top_cell_inventory(source_ly, top_name)
    candidate_cell_inventory = non_top_cell_inventory(cand_ly, top_name)
    cell_inventory_ok = source_cell_inventory == candidate_cell_inventory
    changed_layers, unexpected_layers = geometry_diff(source_ly, source_top, cand_ly, cand_top)
    geometry_ok = not unexpected_layers
    results["checks"].update({"bbox_unchanged": bbox_ok,
                              "stdcell_hierarchy_unchanged": hierarchy_ok,
                              "non_top_cell_inventory_unchanged": cell_inventory_ok,
                              "only_top_routing_layers_changed": geometry_ok})
    if not bbox_ok: results["errors"].append("top-level bbox or DBU changed")
    if not hierarchy_ok: results["errors"].append("non-via instance hierarchy/placement changed")
    if not cell_inventory_ok: results["errors"].append("non-top cell raw shapes or child-instance inventory changed")
    if not geometry_ok: results["errors"].append(f"non-routing layers changed: {unexpected_layers}")

    # Drawing and official MDP reports. Explicit config baselines are honored;
    # otherwise a source report is generated and hash-bound in this build.
    configured_draw = st.get("drawing_baseline")
    configured_mask = st.get("mask_baseline")
    source_copy = build / "source_baseline.gds"
    source_draw_report = build / "source_drawing.lyrdb"
    source_draw_log = build / "source_drawing.log"
    source_mask_gds = build / "source_mask.gds"
    source_mask_report = source_copy.with_name(source_copy.stem + "_mdp.lyrdb")
    source_mask_log = build / "source_mask.log"
    generated_source = None
    if not configured_draw or not configured_mask:
        shutil.copyfile(source, source_copy)
        generated_source = run_drc(source_copy, source_draw_report, source_draw_log,
                                   exp, top_name, source_mask_gds)
    if configured_draw:
        draw_source_report = rel_input(exp, configured_draw)
        if not draw_source_report.is_file(): raise FileNotFoundError(draw_source_report)
        source_draw_markers = helpers.markers(draw_source_report)
        source_draw_log_path = None
    else:
        draw_source_report = source_draw_report
        source_draw_markers = generated_source[0]
        source_draw_log_path = source_draw_log
    if configured_mask:
        mask_source_report = rel_input(exp, configured_mask)
        if not mask_source_report.is_file(): raise FileNotFoundError(mask_source_report)
        source_mask_markers = helpers.markers(mask_source_report)
        source_mask_log_path = None
    else:
        mask_source_report = source_mask_report
        source_mask_markers = generated_source[1]
        source_mask_log_path = source_draw_log

    candidate_drc_input = build / "validation_candidate.gds"
    shutil.copyfile(candidate, candidate_drc_input)
    candidate_draw_report = build / "validation_candidate_drawing.lyrdb"
    candidate_draw_log = build / "validation_candidate_drawing.log"
    candidate_mask_gds = build / "validation_candidate_mask.gds"
    candidate_mask_report = candidate_drc_input.with_name(candidate_drc_input.stem + "_mdp.lyrdb")
    candidate_draw_markers, candidate_mask_markers, _mdp_gds, _mdp_report = run_drc(
        candidate_drc_input, candidate_draw_report, candidate_draw_log, exp, top_name, candidate_mask_gds)
    draw_subset = candidate_draw_markers <= source_draw_markers
    mask_subset = candidate_mask_markers <= source_mask_markers
    results["checks"]["drawing_marker_subset"] = draw_subset
    results["checks"]["mask_marker_subset"] = mask_subset
    if not draw_subset: results["errors"].append("candidate drawing DRC introduces new marker(s)")
    if not mask_subset: results["errors"].append("candidate mask DRC introduces new marker(s)")
    drc_specs = {
        "drawing": {"source_report": str(draw_source_report.relative_to(ROOT)),
                    "source_report_sha256": sha256(draw_source_report),
                    "source_log": str(source_draw_log_path.relative_to(ROOT)) if source_draw_log_path else None,
                    "source_marker_count": len(source_draw_markers),
                    "candidate_report": str(candidate_draw_report.relative_to(ROOT)),
                    "candidate_report_sha256": sha256(candidate_draw_report),
                    "candidate_log": str(candidate_draw_log.relative_to(ROOT)),
                    "candidate_marker_count": len(candidate_draw_markers),
                    "candidate_marker_subset": draw_subset},
        "mask": {"source_report": str(mask_source_report.relative_to(ROOT)),
                 "source_report_sha256": sha256(mask_source_report),
                 "source_log": str(source_mask_log_path.relative_to(ROOT)) if source_mask_log_path else None,
                 "source_marker_count": len(source_mask_markers),
                 "candidate_report": str(candidate_mask_report.relative_to(ROOT)),
                 "candidate_report_sha256": sha256(candidate_mask_report),
                 "candidate_log": str(candidate_draw_log.relative_to(ROOT)),
                 "candidate_marker_count": len(candidate_mask_markers),
                 "candidate_marker_subset": mask_subset}}
    for label, path in (("drawing_source_report", draw_source_report),
                        ("drawing_candidate_report", candidate_draw_report),
                        ("mask_source_report", mask_source_report),
                        ("mask_candidate_report", candidate_mask_report),
                        ("candidate_drc_log", candidate_draw_log)):
        hashes[label] = sha256(path)
    if source_draw_log_path: hashes["source_drawing_log"] = sha256(source_draw_log_path)
    if source_mask_gds.is_file(): hashes["source_mask_gds"] = sha256(source_mask_gds)
    if candidate_mask_gds.is_file(): hashes["candidate_mask_gds"] = sha256(candidate_mask_gds)
    hashes["validation_candidate_copy"] = sha256(candidate_drc_input)
    hashes["candidate_mdp_report"] = sha256(candidate_mask_report)
    hashes["source_mdp_report"] = sha256(mask_source_report)

    for name, outdir in (("source_audit", src_audit_dir), ("audit", cand_audit_dir)):
        for leaf in ("metal_connectivity.json", "actual_pin_map.json", "metal_connectivity.md", "console.log"):
            p = outdir / leaf
            if p.is_file(): hashes[f"{name}/{leaf}"] = sha256(p)

    # Confirm no upstream process or concurrent edit changed any frozen input,
    # candidate, config, helper, toolchain, or source manifest during checks.
    verify()
    unchanged = all(sha256(path) == hashes[key] for key, path in input_paths.items())
    unchanged = unchanged and sha256(source) == st["source_sha256"]
    unchanged = unchanged and sha256(candidate) == initial_candidate_sha
    results["checks"]["all_bound_inputs_unchanged"] = unchanged
    if not unchanged:
        results["errors"].append("a frozen input, candidate, config, helper, toolchain, or manifest changed during checks")
    results.update({"status": "ACCEPTED" if not results["errors"] and all(results["checks"].values()) else "REJECTED",
                    "source_gds": str(source.relative_to(ROOT)), "source_sha256": sha256(source),
                    "candidate_gds": str(candidate.relative_to(ROOT)), "candidate_sha256": sha256(candidate),
                    "source_pair_count": len(source_pairs), "candidate_pair_count": len(candidate_pairs),
                    "source_pairs": sorted(map(list, source_pairs)),
                    "candidate_pairs": sorted(map(list, candidate_pairs)),
                    "removed_pairs": sorted(map(list, source_pairs - candidate_pairs)),
                    "new_pairs": sorted(map(list, candidate_pairs - source_pairs)),
                    "pin_audit": {"source": source_pin_metrics, "candidate": candidate_pin_metrics},
                    "flat_connectivity": {"source_pair_count": len(sconn["pairs"]),
                                          "candidate_pair_count": len(cconn["pairs"]),
                                          "source_opens": sconn["opens"], "candidate_opens": cconn["opens"],
                                          "source_missing": sconn["missing"], "candidate_missing": cconn["missing"],
                                          "source_power_component_counts": sconn["power_component_counts"],
                                          "candidate_power_component_counts": cconn["power_component_counts"],
                                          "source_rail_signal_nets": sconn["rail_signal_nets"],
                                          "candidate_rail_signal_nets": cconn["rail_signal_nets"]},
                    "geometry": {"bbox_um": bbox_signature(cand_top),
                                 "stdcell_hierarchy_unchanged": hierarchy_ok,
                                 "changed_layers": [list(x) for x in changed_layers],
                                 "unexpected_changed_layers": [list(x) for x in unexpected_layers]},
                    "drc": drc_specs, "hashes": hashes, "errors": results["errors"]})
    payload = json.dumps(results, sort_keys=True, separators=(",", ":")).encode()
    results["verification_payload_sha256"] = hashlib.sha256(payload).hexdigest()
    verification = build / "verification.json"
    verification.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"status": results["status"], "checks": results["checks"],
                      "source_pairs": results["source_pair_count"],
                      "candidate_pairs": results["candidate_pair_count"],
                      "report": str(verification.relative_to(ROOT))}, indent=2))
    return 0 if results["status"] == "ACCEPTED" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"validation failed before complete report: {exc}", file=sys.stderr)
        try:
            argv = sys.argv[1:]
            if "--design-root" in argv:
                exp = (ROOT / argv[argv.index("--design-root") + 1]).resolve()
                if exp.is_relative_to(ROOT) and (exp / "config.py").is_file():
                    build = exp / "build"; build.mkdir(parents=True, exist_ok=True)
                    failure = {"status": "ERROR", "errors": [str(exc)], "hashes": {}}
                    for label, path in (("config", exp / "config.py"),
                                        ("validator", Path(__file__)),
                                        ("candidate_gds", build / "candidate.gds")):
                        if path.is_file(): failure["hashes"][label] = sha256(path)
                    target = build / "verification.json"
                    target.write_text(json.dumps(failure, indent=2) + "\n")
                    print(f"Wrote failure report {target.relative_to(ROOT)}", file=sys.stderr)
        except Exception as report_exc:
            print(f"could not write failure report: {report_exc}", file=sys.stderr)
        sys.exit(2)
