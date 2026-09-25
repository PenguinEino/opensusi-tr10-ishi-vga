# Exact stale-via removal audit

This isolated candidate removes only two stale top-level routing `via_1$2` instances from the immutable composed checkpoint. It is an experimental connectivity repair candidate; it does not modify the source checkpoint or claim that the remaining shorts are solved.

The via at (753.3, 600.0) µm joined `_052_`'s M1 branch endpoint `[704.7,599.1,753.3,600.9]` to `_034_`'s M2 trunk `[751.6,537.6,755.0,843.0]`. `_052_`'s intended moved junction via remains at (742.5,600.0). The via at (953.1,255.1) µm joined `_104_`'s M1 branch `[753.3,254.2,953.1,256.0]` to `_139_`'s M2 trunk `[951.4,127.9,954.8,438.7]`; its intended moved via remains at (958.5,255.1). The generator asserts both exact refs and coordinates and verifies every other instance reference and the cell bbox are unchanged.

Full-core KLayout connectivity uses actual LEF pin rectangles/layers and M1/M2/V1 plus GC/CO (AP/AN are ignored). It matched 421 placed instances and all 987 signal pins, with no missing pins or opens. The composed input had 14 short components / 143 distinct net pairs. The candidate has 12 / 141: exactly `_034_`–`_052_` and `_104_`–`_139_` resolve, with no new pair. The component and pair sets, not only their counts, are checked by `verify_removal.py`.

The official pinned drawing and `--mdp` mask reports each have exactly the same two `GC.ANT` items as the composed input, at the BUFTH polygons starting near (1009.3,1626.1) and (1592.5,1626.1) µm. The DRC wrapper exits 1 because these inherited report items remain. XML values are compared from each item's `values/value` nodes and required to be nonempty. The DFFRB constant-input marker is absent in both input and candidate.

## Reproduction

From the repository root:

```sh
python3 scripts/check_toolchain.py
python3 experiments/route_next_audit/remove_stale_vias.py
python3 scripts/routing_diagnostics.py \
  --gds experiments/route_next_audit/build/candidate_no_stale_vias.gds \
  --pins experiments/metal_repair/build/junction_y7296/actual_pin_map.json \
  --shapes experiments/metal_repair/build/junction_y7296/net_shapes.json \
  --placement experiments/phys_desc5/layout/placement.json \
  --out experiments/route_next_audit/build/audit --poly \
  > experiments/route_next_audit/build/connectivity.log 2>&1
python3 scripts/run_apr.py --design-root experiments/routed_checkpoint apr/drc_pdk.py \
  "$PWD/experiments/route_next_audit/build/candidate_no_stale_vias.gds" ishi_vga_core \
  -r "$PWD/experiments/route_next_audit/build/candidate_no_stale_vias.drc.lyrdb" \
  > experiments/route_next_audit/build/drawing_drc.log 2>&1
python3 scripts/run_apr.py --design-root experiments/routed_checkpoint apr/drc_pdk.py \
  "$PWD/experiments/route_next_audit/build/candidate_no_stale_vias.gds" ishi_vga_core \
  -r "$PWD/experiments/route_next_audit/build/candidate_no_stale_vias_mdp_drawing.drc.lyrdb" \
  --mdp --mdp-gds "$PWD/experiments/route_next_audit/build/candidate_no_stale_vias_mdp.gds" \
  > experiments/route_next_audit/build/mask_drc.log 2>&1
python3 experiments/route_next_audit/verify_removal.py
```

`build/removal_manifest.json` records generator provenance and exact deleted refs. `build/verification.json` binds current GDS/source/config/scripts, connectivity reports, and drawing/mask XML hashes and values. The source GDS SHA256 is `9653d8a5b6a9aba7d696e9b881a98042cc749457260c531f3f7ea33b08da7634`.

## Remaining target collisions

This experiment intentionally leaves the other identified via candidates untouched: (747.9,627.0) joins `_051_` M1 to `v[9]` M2; (278.1,190.3) joins `_143_` M1 to `v[9]` M2; (861.3,594.6) joins `_244_` M1 to `h[5]` M2; and (839.7,228.1) joins `h[3]` M1 to `h[5]` M2. The root is evaluating a general top-level via-removal method for these and other cases.
