"""Frozen-input settings for exact top-level route-box pruning."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOX_PRUNE = {
    "source_gds": "experiments/via_prune/build/via_pruned.gds",
    "source_sha256": "bac7c0eb4b19dd017edd43a3599bb80f848d38e349cc0d5e0dedb16f854da94c",
    "expected_source_pairs": 50,
    "top": "ishi_vga_core",
    "placement": "experiments/phys_desc5/layout/placement.json",
    "actual_pins": "experiments/routed_checkpoint/build/audit/actual_pin_map.json",
    "shapes": "experiments/metal_repair/build/junction_y7296/net_shapes.json",
    "source_drc": "experiments/box_prune/build/source_drawing.lyrdb",
    "max_passes": 4,
    "near_pin_um": 5.4,
    "touch_tolerance_um": 0.01,
}
