"""Authorized isolated stale-routing-via removal experiment."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SETTINGS={
  'source_gds':'experiments/routed_checkpoint/build/routed_checkpoint.gds',
  'source_sha256':'9653d8a5b6a9aba7d696e9b881a98042cc749457260c531f3f7ea33b08da7634',
  'reference_layout_gds':'experiments/phys_desc5/build/postrepair_compacted.gds',
  'pins':'experiments/metal_repair/build/junction_y7296/actual_pin_map.json',
  'shapes':'experiments/metal_repair/build/junction_y7296/net_shapes.json',
  'placement':'experiments/phys_desc5/layout/placement.json',
  'top':'ishi_vga_core',
  'remove_vias':[
    {'cell':'via_1$2','x_um':753.3,'y_um':600.0,
     'cause':'stale _052_ M1 branch endpoint via touches _034_ M2 vertical'},
    {'cell':'via_1$2','x_um':953.1,'y_um':255.1,
     'cause':'stale _104_ M1 branch endpoint via touches _139_ M2 vertical'},
  ],
}
