# h[1] local maze-route trial

This trial reconnects the two actual `h[1]` metal components left after removing route-map M2 shapes 2–4 and top-level route vias `via_1$2` at (364.5,400.9) and (364.5,681.0) µm. The frozen input is `experiments/maze_040/build/candidate.gds`, SHA256 `14c35652d06558e3526dd8df401fd7d364b5721f6e0c5d46b4f24846ca4a5023`. The generator's two-component assertion passed; it found a 44-node route with one new V1.

The full actual pin/geometry audit matched all 421 instances and 987 signal pins with no missing pins or opens. Against the frozen input's 44 pairs / 10 short components, the candidate has 43 pairs / 9 components. The exact resolved pair is `_068_`–`h[1]`; no new pair appears. Independent flat extraction using actual LEF pin layers agrees and confirms the rails are unchanged: VDD and VSS each remain separate single components, with only `1'h1` attached to VDD.

Official drawing and mask reports are exact matches for the frozen via-groups baseline: two inherited BUFTH markers in each run (`GC.ANT` in drawing; `WAR06: Floating SG Detected` in mask, near x=1009.3 and 1592.5 µm). The wrappers return nonzero because the reports remain nonempty; this trial adds no marker. Full circuit LVS and timing signoff were not run.

The manifest binds the source/candidate/config/generator/solver, placement and pin inputs, pinned rules and deck, and grid/path bytes. `build/audit/verification.json` records the exact pairsets, rails, geometry edit list, and DRC report hashes. The candidate GDS SHA256 is `70b717f009b7739684a227c8690a8160fe29b43682a13c13b61168e298377a89`.

## Reproduction

From the repository root:

```sh
python3 scripts/check_toolchain.py
python3 scripts/maze_route.py --design-root experiments/maze_h1 \
  > experiments/maze_h1/build.log 2>&1
python3 scripts/routing_diagnostics.py \
  --gds experiments/maze_h1/build/candidate.gds \
  --pins experiments/via_prune/build/audit/actual_pin_map.json \
  --shapes experiments/metal_repair/build/junction_y7296/net_shapes.json \
  --placement experiments/phys_desc5/layout/placement.json \
  --out experiments/maze_h1/build/audit --poly
python3 scripts/run_apr.py --design-root experiments/maze_h1 apr/drc_pdk.py \
  "$PWD/experiments/maze_h1/build/candidate.gds" ishi_vga_core \
  -r "$PWD/experiments/maze_h1/build/drawing.lyrdb"
python3 scripts/run_apr.py --design-root experiments/maze_h1 apr/drc_pdk.py \
  "$PWD/experiments/maze_h1/build/candidate.gds" ishi_vga_core \
  -r "$PWD/experiments/maze_h1/build/mask.lyrdb" --mdp \
  --mdp-gds "$PWD/experiments/maze_h1/build/candidate_mask.gds"
python3 experiments/maze_h1/build/verify_h1.py
```
