# Metal-only repair trials

The best checkpoint for further integration is [`junction_y7296/candidate.gds`](build/junction_y7296/candidate.gds), SHA256 `6f611af77ff390a34d08b3d437b32d06895eae671a9a7bea708d7bc64fef352b`. It moves the internal `_246_` M1 junction and its two vias from y=708.0 to y=729.6 µm, and shortens only that net’s two M2 branches. The input GDS and all real cell pins remain unchanged. Independent pin-aware geometry analysis reduces transitive unintended net pairs from 153 to 143, with 14 mixed components, zero opens, and zero missing signal pins. Simple DRC remains at zero; the pinned official DRC has the same three `GC.ANT` markers as the source and no new markers. The checker still reports 41 short-suspected pin associations, so this checkpoint is not a complete route.

The preserved input is `build/postrepair_compacted.gds`, SHA256 `7ca31f07ead9b36d20af43e1a732cbf51f22ebd1290e15bbb6346c6d124846ba`. Its bounding box is `[-6.3, 0.0, 1777.5, 1756.2] µm` (1783.8 × 1756.2 µm). The accepted checkpoint has the same box. Its reconstructed actual-pin map has 987 signal pins, SHA256 `833890d78b6ec6b848ca60b5982893b8b056ab875188fd16c916138223e69a98`; all 987 land inside their actual LEF pin rectangles. The older 1,017-point pin map is a set of route anchors, not terminal coordinates: all anchors land on their named physical components, while 11 actual signal pins are omitted. The repair script uses the reconstructed map from placement metadata, GDS instance transforms, and the pinned LEF. Reproducible defaults are in [`config.py`](config.py) under `METAL_REPAIR_SETTINGS`; [`config.json`](config.json) is report/provenance data, with source hashes also listed in [`build/source_manifest.json`](build/source_manifest.json).

The `_246_` edit removes the direct `_079_`/`_246_` M1 collision at x=1061.1–1071.9, y=707.1–708.9 µm. Its local edit record is [`edit_manifest.json`](build/junction_y7296/edit_manifest.json). The full GDS component inventory and actual-pin audit are in [`connectivity_components.json`](build/junction_y7296/connectivity_components.json) and [`routing_audit/metal_connectivity.md`](build/junction_y7296/routing_audit/metal_connectivity.md). The exact pair-set differences for all candidates are in [`pair_comparisons.json`](build/pair_comparisons.json); the source-to-checkpoint change removes the ten `_079_` pairs and adds none. The APR connectivity log reports 313 nets / 987 pins and 41 short-suspected associations; no open or missing-pin line is present in [`connectivity_check.log`](build/junction_y7296/connectivity_check.log). Simple DRC is all zero in [`simple_drc.log`](build/junction_y7296/simple_drc.log). The pinned PDK DRC reports three `GC.ANT` markers in [`pdk_drc.log`](build/junction_y7296/pdk_drc.log), byte-identical in marker content to the source baseline, with report [`pdk_drc.lyrdb`](build/junction_y7296/pdk_drc.lyrdb). These three baseline markers are outside the metal edit and are not claimed as resolved.

The bounded `_040_`/`_058_` M2 detour targeted the overlap x=973.0–976.4, y=918.6–992.5 µm. The row-2 alternate M2 lane at x=437.4 µm lies inside `FILLPRI_r2_17` (x=426.6–442.8 µm), but long M1 access bridges create spacing violations. At low/high y=910.8/1028.6 µm, the actual pair set shrank by one more pair (143 to 142), with 13 mixed components and no opens or missing pins, but official DRC rose to 29 markers: 20 `M1.S1`, 6 `ER0045`, and the same 3 baseline `GC.ANT`; there were no M2 or via violations. This is a useful diagnostic checkpoint only and is rejected for integration. Logs and the GDS are in [`detour_040_x437p4`](build/detour_040_x437p4/).

Moving the upper transition farther above the row changes connectivity as well as spacing. With low y=912.6 and high y=1054.7 µm, the actual short count returns to 14 components / 143 pairs and adds a new `_040_`/`v[5]` pair. Official DRC reports 6 `M1.S1`, 6 `ER0045`, and the same 3 `GC.ANT` markers; no M2 or via violations. The other tested high tracks (1040.0, 1044.8, 1050.2, and 1061.0 µm) retain 9–12 simple M1 spacing violations each, with zero simple M2 or V1 violations. All are rejected. Their per-candidate logs, maps, and exact hashes remain under `build/detour_040_*`.

A second bounded trial moved the `_173_` branch around the first `_108_` route/pin overlap using the `FILL2_r1_22` corridor, x=418.5 µm, from y=498.9 to 836.7 µm. It did not improve the pair set: the independent audit remains at 14 components / 143 pairs, zero opens, zero missing pins. The `_108_`/`_173_` short remains through a separate M2 overlap at x=238.6–242.0, y=961.8–992.5 µm. Simple DRC reports 4 M2 width and 2 M2 spacing violations. Official DRC reports 4 `M2.W1`, 2 `M2.S1`, 2 `ER0047`, and the same 3 baseline `GC.ANT` markers. This candidate is rejected and preserved under [`detour_173_x4185_y4989_8367`](build/detour_173_x4185_y4989_8367/).

To reproduce the selected checkpoint and its principal checks from the repository root:

```sh
python3 scripts/check_toolchain.py
python3 scripts/metal_repair.py repair-junction
python3 scripts/routing_diagnostics.py \
  --gds experiments/metal_repair/build/junction_y7296/candidate.gds \
  --pins experiments/metal_repair/build/junction_y7296/actual_pin_map.json \
  --shapes experiments/metal_repair/build/junction_y7296/net_shapes.json \
  --placement experiments/phys_desc5/layout/placement.json \
  --out experiments/metal_repair/build/junction_y7296/routing_audit
python3 scripts/run_apr.py --design-root experiments/metal_repair \
  apr/verify_connectivity_m1m2.py \
  build/junction_y7296/candidate.gds build/junction_y7296/actual_pin_map.json \
  0 5000 1801.2
python3 scripts/run_apr.py --design-root experiments/metal_repair \
  apr/drc_check.py build/junction_y7296/candidate.gds ishi_vga_core
python3 scripts/run_apr.py --design-root experiments/metal_repair \
  apr/drc_pdk.py build/junction_y7296/candidate.gds ishi_vga_core \
  -r build/junction_y7296/pdk_drc.lyrdb
```

The script reads default source paths and track coordinates from `config.py:METAL_REPAIR_SETTINGS`; the command above therefore uses the recorded y=729.6 µm default. Explicit overrides reproduce recorded sensitivity cases, for example `repair-040 --low-y 912.6 --high-y 1054.7`. The measured `top.dbbox()` values are recorded directly in microns. The diagnostic script’s bbox reporting was corrected after an earlier double-scaling error; the reports above use the corrected raw `dbbox` coordinates. No further detour was accepted in this iteration. The next integration source is `junction_y7296/candidate.gds`; any constant-tie patch or combined candidate is a separate root-owned result and must be rechecked as its own GDS.

Implementation provenance: [`config.py`](config.py) owns the reproducible defaults and [`metal_repair.py`](../../scripts/metal_repair.py) is the bounded editor/check harness. Their SHA256 values are listed separately in [`config.json`](config.json); the finalized report-metadata and report-file hashes, along with the input and accepted GDS hashes, are recorded in [`build/implementation_hashes.json`](build/implementation_hashes.json). No accepted GDS was regenerated for these documentation/configuration corrections.
