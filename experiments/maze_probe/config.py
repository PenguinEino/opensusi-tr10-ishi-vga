"""Reproducible inputs for a read-only local maze-routing probe."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GDS = ROOT / "experiments/phys_desc5/build/postrepair_compacted.gds"
NET_SHAPES = ROOT / "experiments/phys_desc5/build/postrepair_shapes.json"
TOP = "ishi_vga_core"

# Parent-selected short: _040_ vertical branch crossing _058_'s row-2 M2.
TARGET_NET = "_040_"
RIPUP_SHAPE_INDICES = (1, 2, 3)  # M2 x=973..976.4, y=870..1369.8
BLOCKER_NET = "_058_"
START_UM = (974.7, 870.0)       # existing M1 trunk / M2 branch junction
GOAL_UM = (974.7, 1369.8)       # branch landing immediately below output pin
SEARCH_UM = (900.0, 840.0, 1050.0, 1400.0)

# Grid pitch/origin are design settings. Rule values are imported at runtime
# from the locked APRtools rules.py; they are deliberately not duplicated here.
GRID_UM = 2.7
