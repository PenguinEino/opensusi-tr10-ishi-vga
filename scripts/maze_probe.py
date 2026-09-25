#!/usr/bin/env python3
"""Read-only ownership/obstacle preflight for a local two-layer maze trial.

This prototype never edits its input GDS. It checks whether an explicitly
selected route-map rectangle has a unique top-cell shape owner, then produces
an obstacle snapshot excluding only those top-cell shapes. Placed-cell and
PCell geometry remain obstacles. Via ownership is not represented by
net_shapes.json, so the probe refuses to emit modified GDS or claim a
connectivity-complete reroute.
"""
from __future__ import annotations
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/APRtools/apr"))
sys.path.insert(0, str(ROOT / "experiments/maze_probe"))
import klayout.db as db
import rules
import config


LAYERS = {"M1": rules.M1, "M2": rules.M2}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def um_box_to_dbu(box, dbu):
    return db.Box(*(int(round(v / dbu)) for v in box))


def box_tuple(box):
    return (box.left, box.bottom, box.right, box.top)


def get_selected_shapes(shape_map):
    src = shape_map.get(config.TARGET_NET, [])
    selected = []
    for i in config.RIPUP_SHAPE_INDICES:
        if i >= len(src):
            raise ValueError(f"shape index {i} outside {config.TARGET_NET} map")
        rec = src[i]
        if len(rec) != 5 or rec[0] not in LAYERS:
            raise ValueError(f"unexpected route record: {rec!r}")
        selected.append((i, rec[0], tuple(float(x) for x in rec[1:])))
    return selected


def iter_recursive_boxes(top, layer_idx):
    it = top.begin_shapes_rec(layer_idx)
    while not it.at_end():
        s = it.shape()
        if s.is_box():
            yield s.box.transformed(it.trans()), (it.cell_index() != top.cell_index())
        elif s.is_polygon():
            yield s.polygon.transformed(it.trans()).bbox(), (it.cell_index() != top.cell_index())
        elif s.is_path():
            yield s.path.transformed(it.trans()).polygon().bbox(), (it.cell_index() != top.cell_index())
        it.next()


def inspect():
    if not config.GDS.is_file() or not config.NET_SHAPES.is_file():
        raise FileNotFoundError("configured GDS/net-shapes input missing")
    shape_map = json.loads(config.NET_SHAPES.read_text())
    selected = get_selected_shapes(shape_map)

    # A record may be removed only if it is not also claimed by any other net.
    other_claims = Counter()
    for net, records in shape_map.items():
        if net == config.TARGET_NET:
            continue
        for rec in records:
            if len(rec) == 5 and rec[0] in LAYERS:
                other_claims[(rec[0], tuple(round(float(v), 4) for v in rec[1:]))] += 1

    ly = db.Layout()
    ly.read(str(config.GDS))
    top = ly.cell(config.TOP)
    if top is None:
        raise ValueError(f"top cell {config.TOP!r} absent")
    exclusions = {tag: set() for tag in LAYERS}
    selected_report = []
    for index, tag, rect_um in selected:
        rounded = tuple(round(x, 4) for x in rect_um)
        if other_claims[(tag, rounded)]:
            raise ValueError(f"{tag} {rounded} also claimed by another net")
        idx = ly.layer(*LAYERS[tag])
        target = um_box_to_dbu(rect_um, ly.dbu)
        matches = [s for s in top.shapes(idx).each() if s.is_box() and s.box == target]
        if len(matches) != 1:
            raise ValueError(f"{config.TARGET_NET}[{index}] expected one top-level box, found {len(matches)}")
        exclusions[tag].add(box_tuple(target))
        selected_report.append({"net": config.TARGET_NET, "index": index,
                                "layer": tag, "box_um": list(rect_um),
                                "top_level_exact_matches": len(matches)})

    # Collect flattened obstacles from the whole design, excluding only exact
    # target route boxes at identity/top level. Since the recursive iterator
    # does not expose a stable route owner, subtract exact boxes geometrically
    # but first preserve any same-layer cell/PCell shape that intersects them.
    # Such intersections make safe exclusion ambiguous, so fail closed.
    layer_report = {}
    for tag, pair in LAYERS.items():
        idx = ly.layer(*pair)
        selected_boxes = exclusions[tag]
        blockers = []
        for b, nested in iter_recursive_boxes(top, idx):
            if not nested and box_tuple(b) in selected_boxes:
                continue
            if any(b.overlaps(um_box_to_dbu(box, ly.dbu)) for _, t, box in selected if t == tag):
                blockers.append(b)
        all_boxes = list(iter_recursive_boxes(top, idx))
        retained = [(b, nested) for b, nested in all_boxes
                    if not (not nested and box_tuple(b) in selected_boxes)]
        layer_report[tag] = {
            "flattened_shape_count_before": len(all_boxes),
            "selected_boxes_removed": len(selected_boxes),
            "flattened_shape_count_after": len(retained),
            "preserved_overlapping_cell_or_route_shapes": len(blockers),
            "obstacle_boxes_um": [[round(b.left*ly.dbu, 4), round(b.bottom*ly.dbu, 4),
                                   round(b.right*ly.dbu, 4), round(b.top*ly.dbu, 4)]
                                  for b, _ in retained],
        }
    return {
        "status": "SAFE_RIPUP_PREFLIGHT_ONLY",
        "warning": "No GDS was written; via ownership is absent from net_shapes.json.",
        "inputs": {"gds": str(config.GDS.relative_to(ROOT)), "gds_sha256": sha256(config.GDS),
                   "net_shapes": str(config.NET_SHAPES.relative_to(ROOT)),
                   "net_shapes_sha256": sha256(config.NET_SHAPES)},
        "target_net": config.TARGET_NET,
        "blocker_net": config.BLOCKER_NET,
        "selected_route_shapes": selected_report,
        "layers": layer_report,
        "maze_parameters": {"grid_um": config.GRID_UM, "start_um": config.START_UM,
                            "goal_um": config.GOAL_UM, "search_um": config.SEARCH_UM,
                            "M1_min_width_um": rules.M1_WIDTH_MIN,
                            "M1_min_space_um": rules.M1_SPACE_MIN,
                            "M2_min_width_um": rules.M2_WIDTH_MIN,
                            "M2_min_space_um": rules.M2_SPACE_MIN,
                            "V1_cut_um": rules.V1_CUT,
                            "V1_M1_enclosure_um": rules.V1_ENC_M1,
                            "V1_M2_enclosure_um": rules.V1_ENC_M2},
    }


def main():
    report = inspect()
    out = ROOT / "experiments/maze_probe/preflight.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['status']}: wrote {out.relative_to(ROOT)}")
    for item in report["selected_route_shapes"]:
        print(f"rip-up candidate {item['net']}[{item['index']}] {item['layer']} {item['box_um']}")
    print("No input GDS modified. Via instances are not safely attributable from this map.")


if __name__ == "__main__":
    main()
