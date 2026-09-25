#!/usr/bin/env python3
"""Annotate the adopted eight-port core; derived from frozen label_core_ports.py."""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/APRtools/apr"))
import klayout.db as db
import lef_parser
import rules
from check_toolchain import verify


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_literal_config(path: Path) -> dict:
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "CORE_PORT_LABELS" for t in node.targets):
            value = ast.literal_eval(node.value)
            if not isinstance(value, dict):
                raise ValueError("CORE_PORT_LABELS must be a literal dictionary")
            return value
    raise ValueError(f"No literal CORE_PORT_LABELS assignment in {path}")


def workspace_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"input escapes workspace: {value}")
    return path


def expected_spice_ports(path: Path, top_name: str) -> list[str]:
    text = path.read_text(errors="strict")
    match = re.search(rf"(?im)^\s*\.subckt\s+{re.escape(top_name)}\s+([^\n]+)", text)
    if not match:
        raise ValueError(f"reference SPICE has no .SUBCKT {top_name}")
    return match.group(1).split()


def placement_and_lef(path: Path):
    place = json.loads(path.read_text())
    instances = {inst["name"]: inst for row in place["rows"] for inst in row}
    lef = lef_parser.parse_lef(ROOT / "tools/APRtools/stdcell/v59_4/TR-1um_cells.lef")
    return instances, lef


def make_connectivity(layout, top):
    layers = {}
    for name in ("M1", "M2", "V1", "GC", "CO"):
        region = db.Region(top.begin_shapes_rec(layout.layer(*getattr(rules, name)))).merged()
        layers[name] = region
    l2n = db.LayoutToNetlist(top.name, layout.dbu)
    for name, region in layers.items():
        l2n.register(region, name)
        l2n.connect(region)
    for a, b in (("M1", "V1"), ("M2", "V1"), ("GC", "CO"), ("CO", "M1")):
        l2n.connect(layers[a], layers[b])
    l2n.extract_netlist()

    def node(layer_name: str, x_um: float, y_um: float):
        point = db.Point(round(x_um / layout.dbu), round(y_um / layout.dbu))
        net = l2n.probe_net(layers[layer_name], point)
        return net.expanded_name() if net else None
    return layers, node


def actual_power_labels(layout, top):
    labels = {"vdd": [], "vss": []}
    for inst in top.each_inst():
        if inst.cell.name.lower().startswith("via_"):
            continue
        layer_index = layout.layer(*rules.M1_LBL)
        for shape in inst.cell.shapes(layer_index).each():
            if not shape.is_text() or shape.text.string.lower() not in labels:
                continue
            point = inst.trans * db.Point(shape.text.trans.disp.x, shape.text.trans.disp.y)
            labels[shape.text.string.lower()].append(
                (point.x * layout.dbu, point.y * layout.dbu, inst.cell.name))
    return labels


def region_fingerprints(layout, top):
    result = {}
    for info in layout.layer_infos():
        layer_index = layout.layer(info)
        region = db.Region(top.begin_shapes_rec(layer_index)).merged()
        result[(info.layer, info.datatype)] = region.to_s()
    return result


def shapes_fingerprint(cell, layout):
    rows = []
    for info in layout.layer_infos():
        layer_index = layout.layer(info)
        for shape in cell.shapes(layer_index).each():
            if not shape.is_text():
                rows.append((info.layer, info.datatype, shape.to_s()))
    return sorted(rows)


def text_inventory(cell, layout):
    rows = []
    for label_layer in (rules.M1_LBL, rules.M2_LBL):
        index = layout.layer(*label_layer)
        for shape in cell.shapes(index).each():
            if shape.is_text():
                tr = shape.text.trans
                rows.append((shape.text.string, label_layer[0], label_layer[1],
                             tr.disp.x, tr.disp.y, tr.to_s()))
            else:
                raise ValueError(f"non-text top shape found on label layer {label_layer}")
    return sorted(rows)


def hierarchy_fingerprint(top):
    rows = []
    for inst in top.each_inst():
        rows.append((inst.cell.name, inst.trans.to_s(), inst.na, inst.nb,
                     inst.a.x, inst.a.y, inst.b.x, inst.b.y))
    return sorted(rows)


def non_top_inventory(layout, top_name):
    inventory = {}
    for cell in layout.each_cell():
        if cell.name == top_name:
            continue
        shapes = []
        for info in layout.layer_infos():
            index = layout.layer(info)
            for shape in cell.shapes(index).each():
                shapes.append((info.layer, info.datatype, shape.to_s()))
        children = [(inst.cell.name, inst.trans.to_s(), inst.na, inst.nb,
                     inst.a.x, inst.a.y, inst.b.x, inst.b.y)
                    for inst in cell.each_inst()]
        inventory[cell.name] = (sorted(shapes), sorted(children))
    return inventory


def drc_markers(path: Path):
    markers = set()
    for item in ET.parse(path).getroot().iter("item"):
        category = item.findtext("category")
        values = tuple(sorted(v.text.strip() for v in item.findall("./values/value")
                              if v.text and v.text.strip()))
        if not category or not values:
            raise ValueError(f"DRC marker lacks category/value in {path}")
        markers.add((category.strip(), values))
    return markers


def run_official_drc(gds: Path, build: Path, design_root: Path, stem: str):
    input_copy = build / f"{stem}.gds"
    if gds.resolve() != input_copy.resolve():
        shutil.copyfile(gds, input_copy)
    drawing = build / f"{stem}_drawing.lyrdb"
    log = build / f"{stem}_drc.log"
    mdp_gds = build / f"{stem}_mdp_output.gds"
    mdp = input_copy.with_name(input_copy.stem + "_mdp.lyrdb")
    for stale in (drawing, log, mdp_gds, mdp):
        stale.unlink(missing_ok=True)
    command = [sys.executable, str(ROOT / "scripts/run_apr.py"),
               "--design-root", str(design_root.relative_to(ROOT)), "apr/drc_pdk.py",
               str(input_copy), "ishi_vga_core", "-r", str(drawing), "--mdp",
               "--mdp-gds", str(mdp_gds)]
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    log.write_text(proc.stdout + proc.stderr)
    summary = proc.stdout + proc.stderr
    if (proc.returncode not in (0, 1) or not drawing.is_file() or not mdp.is_file() or
            not mdp_gds.is_file() or mdp_gds.stat().st_size < 1024):
        raise RuntimeError(f"official drawing/MDP did not produce fresh reports; see {log}")
    if "DRC:" not in summary or "MDP:" not in summary or "run_IP62" not in summary:
        raise RuntimeError(f"official DRC/MDP summary missing; see {log}")
    return {"input_copy": input_copy, "drawing": drawing, "mdp": mdp,
            "mdp_gds": mdp_gds, "log": log,
            "drawing_markers": drc_markers(drawing), "mdp_markers": drc_markers(mdp),
            "exit_code": proc.returncode}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design-root", required=True)
    args = parser.parse_args()
    verify()
    design = (ROOT / args.design_root).resolve()
    if not design.is_relative_to(ROOT) or not (design / "config.py").is_file():
        raise ValueError("--design-root must be a workspace experiment with config.py")
    config_path = design / "config.py"
    cfg = read_literal_config(config_path)
    required = ("top", "source_gds", "source_sha256", "actual_pin_map",
                "actual_pin_map_sha256", "placement", "placement_sha256",
                "reference_spice", "reference_spice_sha256", "expected_ports")
    absent = [key for key in required if key not in cfg]
    if absent:
        raise ValueError(f"CORE_PORT_LABELS missing keys: {absent}")

    source = workspace_path(cfg["source_gds"])
    pins_path = workspace_path(cfg["actual_pin_map"])
    placement_path = workspace_path(cfg["placement"])
    spice_path = workspace_path(cfg["reference_spice"])
    bound_paths = {"source_gds": source, "actual_pin_map": pins_path,
                   "placement": placement_path, "reference_spice": spice_path,
                   "config": config_path, "generator": Path(__file__),
                   "rules": ROOT / "tools/APRtools/apr/rules.py",
                   "cell_lef": ROOT / "tools/APRtools/stdcell/v59_4/TR-1um_cells.lef",
                   "toolchain_lock": ROOT / "toolchain.lock.json",
                   "toolchain_check": ROOT / "scripts/check_toolchain.py",
                   "apr_wrapper": ROOT / "scripts/run_apr.py",
                   "drawing_deck": ROOT / "tools/TR-1um/libs.tech/klayout/tech/drc/run.drc",
                   "mdp_deck": ROOT / "tools/TR-1um/libs.tech/klayout/tech/drc/run_mdp.drc",
                   "mask_deck": ROOT / "tools/TR-1um/libs.tech/klayout/tech/drc/run_IP62.drc"}
    initial_hashes = {key: sha(path) for key, path in bound_paths.items()}
    expected = list(cfg["expected_ports"])
    for name, path, expected_hash in (
            ("source_gds", source, cfg["source_sha256"]),
            ("actual_pin_map", pins_path, cfg["actual_pin_map_sha256"]),
            ("placement", placement_path, cfg["placement_sha256"]),
            ("reference_spice", spice_path, cfg["reference_spice_sha256"])):
        if sha(path) != expected_hash:
            raise RuntimeError(f"{name} SHA256 mismatch: {sha(path)} != {expected_hash}")
    top_name = cfg["top"]
    ref_ports = expected_spice_ports(spice_path, top_name)
    if ref_ports != expected:
        raise RuntimeError(f"configured port order differs from reference SPICE: {expected} != {ref_ports}")
    expected_signal_ports = [p for p in expected if p not in ("vdd", "vss")]
    if len(expected) != 8 or len(set(expected)) != len(expected):
        raise RuntimeError("expected exactly 8 unique core ports")

    pins = json.loads(pins_path.read_text())
    instances, lef = placement_and_lef(placement_path)
    layout = db.Layout()
    layout.read(str(source))
    top = layout.cell(top_name)
    if top is None:
        raise RuntimeError(f"source GDS lacks top cell {top_name}")
    dbu = layout.dbu
    before_text = text_inventory(top, layout)
    if before_text:
        raise RuntimeError(f"source top already has labels; refusing ambiguous port annotation: {before_text}")
    layers, probe = make_connectivity(layout, top)
    label_specs = []

    # Bind every scalar signal label to an actual placed LEF pin point and its
    # physical M1/M2 layer; require that the point probes actual conductor.
    for port in expected_signal_ports:
        records = pins.get(port)
        if not records:
            raise RuntimeError(f"actual pin map has no signal pin for port {port}")
        choices = sorted(records, key=lambda rec: (rec[0], rec[1], rec[2], rec[3]))
        selected = None
        for inst_name, pin_name, x_um, y_um in choices:
            inst = instances.get(inst_name)
            if inst is None or inst["type"] not in lef or pin_name not in lef[inst["type"]]["pins"]:
                continue
            metals = {rect[0] for rect in lef[inst["type"]]["pins"][pin_name]["rects"]
                      if rect[0] in ("METAL1", "METAL2")}
            if len(metals) != 1:
                continue
            metal = next(iter(metals))
            layer_name = {"METAL1": "M1", "METAL2": "M2"}[metal]
            point = db.Point(round(float(x_um) / dbu), round(float(y_um) / dbu))
            if probe(layer_name, float(x_um), float(y_um)) is None:
                continue
            selected = {"port": port, "instance": inst_name, "pin": pin_name,
                        "xy_um": [float(x_um), float(y_um)], "layer": layer_name,
                        "label_layer": getattr(rules, layer_name + "_LBL"),
                        "net_identity": probe(layer_name, float(x_um), float(y_um)),
                        "point_dbu": [point.x, point.y]}
            break
        if selected is None:
            raise RuntimeError(f"no conductor-backed actual LEF pin found for {port}")
        label_specs.append(selected)

    # Locate every placed cell's real supply labels. All labels on each rail
    # must belong to one and only one extracted physical component.
    supply_labels = actual_power_labels(layout, top)
    supply_nodes = {}
    for rail in ("vdd", "vss"):
        choices = sorted(supply_labels[rail], key=lambda rec: (rec[0], rec[1], rec[2]))
        if not choices:
            raise RuntimeError(f"no actual standard-cell {rail} labels found")
        nodes = set()
        for x_um, y_um, _cell_name in choices:
            net_name = probe("M1", x_um, y_um)
            if net_name is None:
                raise RuntimeError(f"actual {rail} label does not land on M1: {(x_um, y_um)}")
            nodes.add(net_name)
        if len(nodes) != 1:
            raise RuntimeError(f"actual {rail} labels span {len(nodes)} components")
        supply_nodes[rail] = next(iter(nodes))
        x_um, y_um, chosen_cell = choices[0]
        label_specs.append({"port": rail, "instance_cell": chosen_cell,
                            "xy_um": [x_um, y_um], "layer": "M1",
                            "label_layer": rules.M1_LBL,
                            "net_identity": supply_nodes[rail],
                            "point_dbu": [round(x_um / dbu), round(y_um / dbu)]})
    if supply_nodes["vdd"] == supply_nodes["vss"]:
        raise RuntimeError("extracted VDD and VSS labels resolve to the same component")

    # Ensure each chosen port name/layer is unique and non-conflicting.
    if {s["port"] for s in label_specs} != set(expected) or len(label_specs) != len(expected):
        raise RuntimeError("port label mapping does not cover exactly the expected 8 ports")
    for spec in label_specs:
        label_layer = layout.layer(*spec["label_layer"])
        text = db.Text(spec["port"], db.Trans(db.Point(*spec["point_dbu"])))
        top.shapes(label_layer).insert(text)

    build = design / "build"
    build.mkdir(parents=True, exist_ok=True)
    candidate = build / "labeled_core.gds"
    options = db.SaveLayoutOptions()
    options.gds2_write_timestamps = False
    layout.write(str(candidate), options)
    if sha(source) != cfg["source_sha256"]:
        raise RuntimeError("frozen raw source changed during label generation")

    # Reload both files: verify that labels are the sole change, including all
    # raw non-text shapes and the entire hierarchy.
    source_layout = db.Layout(); source_layout.read(str(source)); source_top = source_layout.cell(top_name)
    output_layout = db.Layout(); output_layout.read(str(candidate)); output_top = output_layout.cell(top_name)
    if source_layout.dbu != output_layout.dbu:
        raise RuntimeError("DBU changed during output serialization")
    geometry_same = region_fingerprints(source_layout, source_top) == region_fingerprints(output_layout, output_top)
    hierarchy_same = hierarchy_fingerprint(source_top) == hierarchy_fingerprint(output_top)
    top_shapes_same = shapes_fingerprint(source_top, source_layout) == shapes_fingerprint(output_top, output_layout)
    non_top_same = non_top_inventory(source_layout, top_name) == non_top_inventory(output_layout, top_name)
    before_labels = text_inventory(source_top, source_layout)
    after_labels = text_inventory(output_top, output_layout)
    expected_label_rows = sorted((s["port"], s["label_layer"][0], s["label_layer"][1],
                                  s["point_dbu"][0], s["point_dbu"][1],
                                  db.Text(s["port"], db.Trans(db.Point(*s["point_dbu"]))).trans.to_s())
                                 for s in label_specs)
    if not geometry_same or not hierarchy_same or not top_shapes_same or not non_top_same:
        raise RuntimeError("label output changed geometry, hierarchy, or non-text cell shapes")
    if before_labels or after_labels != expected_label_rows:
        raise RuntimeError(f"top text-label delta is not exactly the expected 8 ports: {after_labels}")
    candidate_sha_before_checks = sha(candidate)

    # Re-probe each serialized label point against the corresponding physical
    # conductor. Text annotations never create connectivity by themselves.
    out_layers, out_probe = make_connectivity(output_layout, output_top)
    for spec in label_specs:
        x, y = spec["xy_um"]
        if out_probe(spec["layer"], x, y) != spec["net_identity"]:
            raise RuntimeError(f"serialized label {spec['port']} is not on its intended extracted conductor")

    # Official drawing + MDP on a unique source copy and labeled candidate.
    source_drc = run_official_drc(source, build, design, "source_core")
    candidate_drc = run_official_drc(candidate, build, design, "labeled_core")
    draw_subset = candidate_drc["drawing_markers"] <= source_drc["drawing_markers"]
    mdp_subset = candidate_drc["mdp_markers"] <= source_drc["mdp_markers"]
    if not draw_subset or not mdp_subset:
        raise RuntimeError("port annotation added official drawing or MDP marker(s)")

    verify()
    hashes = {key: sha(path) for key, path in bound_paths.items()}
    candidate_sha_after_checks = sha(candidate)
    unchanged = hashes == initial_hashes and candidate_sha_before_checks == candidate_sha_after_checks
    if not unchanged:
        raise RuntimeError("a source, config, reference, rules, or deck input changed during the run")
    hashes["candidate_gds"] = sha(candidate)
    report = {
        "status": "ACCEPTED" if geometry_same and hierarchy_same and top_shapes_same and non_top_same and draw_subset and mdp_subset else "REJECTED",
        "top": top_name,
        "reference_spice_ports": ref_ports,
        "port_labels": label_specs,
        "checks": {"exact_12_expected_labels": after_labels == expected_label_rows,
                   "all_polygon_regions_unchanged": geometry_same,
                   "top_nontext_shapes_unchanged": top_shapes_same,
                   "hierarchy_unchanged": hierarchy_same,
                   "all_non_top_cell_shapes_and_children_unchanged": non_top_same,
                   "signal_labels_on_actual_pin_conductors": all(
                       s["port"] in ("vdd", "vss") or bool(s["net_identity"]) for s in label_specs),
                   "vdd_vss_actual_labels_are_separate_single_components": len(supply_nodes) == 2 and supply_nodes["vdd"] != supply_nodes["vss"],
                   "drawing_marker_subset": draw_subset,
                   "mask_marker_subset": mdp_subset,
                   "candidate_unchanged_during_checks": candidate_sha_before_checks == candidate_sha_after_checks,
                   "all_bound_inputs_unchanged": unchanged},
        "power_components": supply_nodes,
        "drc": {"source": {"exit_code": source_drc["exit_code"],
                            "drawing_count": len(source_drc["drawing_markers"]),
                            "drawing_markers": sorted([list(x) for x in source_drc["drawing_markers"]]),
                            "mdp_count": len(source_drc["mdp_markers"]),
                            "mdp_markers": sorted([list(x) for x in source_drc["mdp_markers"]])},
                "candidate": {"exit_code": candidate_drc["exit_code"],
                              "drawing_count": len(candidate_drc["drawing_markers"]),
                              "drawing_markers": sorted([list(x) for x in candidate_drc["drawing_markers"]]),
                              "mdp_count": len(candidate_drc["mdp_markers"]),
                              "mdp_markers": sorted([list(x) for x in candidate_drc["mdp_markers"]])}},
        "paths": {"source_gds": str(source.relative_to(ROOT)),
                  "candidate_gds": str(candidate.relative_to(ROOT)),
                  "source_spice": str(spice_path.relative_to(ROOT)),
                  "source_drawing_report": str(source_drc["drawing"].relative_to(ROOT)),
                  "source_mdp_report": str(source_drc["mdp"].relative_to(ROOT)),
                  "candidate_drawing_report": str(candidate_drc["drawing"].relative_to(ROOT)),
                  "candidate_mdp_report": str(candidate_drc["mdp"].relative_to(ROOT))},
        "hashes": hashes}
    payload = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    report["verification_payload_sha256"] = hashlib.sha256(payload).hexdigest()
    (build / "label_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "candidate": str(candidate.relative_to(ROOT)),
                      "drawing_markers": report["drc"]["candidate"]["drawing_count"],
                      "mdp_markers": report["drc"]["candidate"]["mdp_count"],
                      "report": str((build / "label_report.json").relative_to(ROOT))}, indent=2))
    return 0 if report["status"] == "ACCEPTED" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"port label generation failed: {exc}", file=sys.stderr)
        sys.exit(2)
