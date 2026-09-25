# Physical area and routing experiments

Updated 2026-09-25. This report records placement and diagnostic routing only. Every APRtools entry point was invoked through `scripts/run_apr.py --design-root` after `python3 scripts/check_toolchain.py` passed.

## Result

The only measured candidate whose step6 diagnostic compacted BBox fit within 1800 × 1800 µm was `phys_desc5`: 1783.8 × 1750.8 µm. Its connectivity checker still reported 65 short-suspected problems, so this is diagnostic geometry, not a submission-ready layout.

Applying the existing step7 repair flow to `phys_desc5` ran all 60 iterations in approximately 20 minutes (estimate; the original interactive session had no timer). It moved 35 vertical and 10 horizontal segments, reached the iteration limit without convergence, and left 65 raw box conflicts plus 41 component-level shorted net pairs. The independent step7 connectivity check also reported 41 problems. After separately squeezing the repaired GDS, the measured BBox was 1783.8 × 1756.2 µm; the simple DRC reported zero for all seven checks. Connectivity problems remain, so this GDS is not submission-ready.

## Measurements

All rows use seed 4 except `phys_i` (seed 7). `CORE_WIDTH_TRACKS` uses the upstream 5.4 µm track pitch: 328 tracks = 1771.2 µm. Occupancy is the maximum sum of placed standard-cell widths in any row, excluding filler and tap cells. “Conn.” is the step6 `verify_connectivity_m1m2.py` problem report count; it is not an independent count of physical short locations. Simple DRC is the upstream flow’s approximate M1/M2/V1 checker, not the official PDK deck.

| Experiment | Netlist SHA256 (prefix) | Rows × tracks | Restarts / order passes / balance | PRL | Cut | Max row (µm) | Step6 BBox (µm) | Conn. | Simple DRC |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| phys_a | `51a1f54fe318…` | 7 × 296 | 80 / 20 / 0.08 | 10 | 361.0 | 1123.2 | 1611.0 × 2527.0 | 89 | 0 (7 checks) |
| phys_b | `51a1f54fe318…` | 6 × 296 | 80 / 20 / 0.08 | 10 | 306.0 | 1312.2 | 1611.0 × 1993.1 | 74 | 0 (7 checks) |
| phys_c | `51a1f54fe318…` | 6 × 328 | 80 / 20 / 0.08 | 10 | 306.0 | 1312.2 | 1783.8 × 1885.1 | 44 | 0 (7 checks) |
| phys_d | `51a1f54fe318…` | 6 × 296 | 80 / 20 / 0.08 | 5 | 306.0 | 1312.2 | 1611.0 × 2182.1 | 45 | 0 (7 checks) |
| phys_e | `51a1f54fe318…` | 5 × 328 | 160 / 20 / 0.02 | 10 | 276.0 | 1490.4 | 1783.8 × 1837.2 | 79 | 0 (7 checks) |
| phys_h | `51a1f54fe318…` | 5 × 328 | 800 / 40 / 0.02 | 10 | 255.0 | 1490.4 | 1783.8 × 1950.6 | 78 | 0 (7 checks) |
| phys_i | `51a1f54fe318…` | 5 × 328 | 160 / 40 / 0.05 | 10 | 232.0 | 1533.6 | 1783.8 × 1842.6 | 52 | 0 (7 checks) |
| phys_hv6 | `1d4de09df964…` | 6 × 328 | 80 / 20 / 0.08 | 10 | 321.0 | 1236.6 | 1783.8 × 2090.3 | 68 | 0 (7 checks) |
| phys_hv5 | `1d4de09df964…` | 5 × 328 | 160 / 20 / 0.02 | 10 | 270.0 | 1404.0 | 1783.8 × 1848.0 | 74 | 0 (7 checks) |
| phys_desc5 | `9e2b7928ea22…` | 5 × 328 | 160 / 20 / 0.02 | 10 | 245.0 | 1393.2 | 1783.8 × 1750.8 | 65 | 0 (7 checks) |

`phys_a`–`phys_e`, `phys_h`, and `phys_i` use `experiments/arch_offset_h80/out/ishi_vga_core_pnr.v` (311 cells, 433987 µm²; SHA256 `51a1f54fe3187ca32cb8664a61ea13a8a539305c943e0003f3440bbfc2e09632`). `phys_hv6` and `phys_hv5` use `experiments/combine_direct_bounds_h80_v500/out/ishi_vga_core_pnr.v` (285 cells, 409289 µm²; SHA256 `1d4de09df9648e29f225cd149e806b3b61112ed53896090fbcf299574a695f5d`). `phys_desc5` uses `experiments/descending_h79_v500/out/ishi_vga_core_pnr.v` (282 cells, 407684 µm²; SHA256 `9e2b7928ea22297300fe376483f21b778647caae48ffd51ac68c75186cec0592`).

### Repaired `phys_desc5` measurements

- Step7 output: `experiments/phys_desc5/layout/step7/route_step_3_ripup_reroute.gds`.
- Step7 checker: 41 connectivity problems; M1/M2 width and spacing, V1 spacing/enclosure/GA spacing/cut checks all 0.
- Independent compacted GDS: `experiments/phys_desc5/build/postrepair_compacted.gds`; BBox `(-6.300, 0.000) – (1777.500, 1756.200) µm`, width 1783.8 µm, height 1756.2 µm.
- Postrepair connectivity: 41 problems. Postrepair simple DRC: all seven counters 0.
- GDS SHA256: `7ca31f07ead9b36d20af43e1a732cbf51f22ebd1290e15bbb6346c6d124846ba`.
- Logs: `experiments/phys_desc5/build/route_step7.log`, `postrepair_compaction.log`, `postrepair_connectivity.log`, and `postrepair_simple_drc.log`.

Remaining physical work is substantial: 41 connectivity problems remain, and official DRC/LVS/parasitic STA and organizer-template integration have not been run. Step7 consumed about 20 minutes for one 60-iteration attempt. The step7 log is explicitly a partial interactive capture: iterations 11–23 are missing and a few initial lines are summarized. The final checker output and results above were captured separately in full. Step6 and step7 simple DRC checks are not official DRC; no official DRC, LVS, or parasitic STA was run by this physical experiment.

## Reproduction

```sh
python3 scripts/check_toolchain.py
python3 scripts/phys_area_sweep.py A
python3 scripts/phys_area_sweep.py B
python3 scripts/phys_area_sweep.py C
python3 scripts/phys_area_sweep.py D
python3 scripts/phys_area_sweep.py E
python3 scripts/phys_area_sweep.py F
python3 scripts/phys_area_sweep.py G
python3 scripts/phys_area_sweep.py H
python3 scripts/phys_area_sweep.py I
python3 scripts/phys_area_sweep.py J
```

Each run writes an independent design under `experiments/phys_*`, a complete `config.py`, a source manifest with netlist SHA256 and settings, placement/route logs, a diagnostic compressed GDS, and `build/physical_report.json`. The script does not alter the root netlist, root config, root layout, or APRtools source.

For the selected candidate, after case J has generated step6:

```sh
python3 scripts/run_apr.py --design-root experiments/phys_desc5 apr/route.py --from 7 --to 7
python3 scripts/run_apr.py --design-root experiments/phys_desc5 apr/squeeze_channels.py \
  --in-gds layout/step7/route_step_3_ripup_reroute.gds \
  -o build/postrepair_compacted.gds \
  --pin-map-in layout/pin_map_rr.json --pin-map-out build/postrepair_pins.json \
  --net-shapes-in layout/net_shapes_rr.json --net-shapes-out build/postrepair_shapes.json
python3 scripts/run_apr.py --design-root experiments/phys_desc5 apr/drc_check.py \
  build/postrepair_compacted.gds ishi_vga_core
python3 scripts/run_apr.py --design-root experiments/phys_desc5 apr/verify_connectivity_m1m2.py \
  build/postrepair_compacted.gds build/postrepair_pins.json 0 1766.2 1801.2
```

The last scan bounds are specific to this measured artifact: bbox top + 10 µm, row width + 30 µm, as used by the upstream checking flow. Recompute them if geometry changes. A zero process exit code does not mean the connectivity checker passed; inspect its problem report.
