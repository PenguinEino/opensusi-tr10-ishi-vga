# Top-level route-via pruning review

This candidate removes 17 redundant top-level `via_1$2` instances from the composed `routed_checkpoint.gds`. The source GDS is unchanged. The generator tests one via location at a time, accepts only deletions that strictly shrink the current actual signal-net pair set without introducing missing pins or opens, preserve the VDD/VSS component and attached-signal sets, and add no marker to the official pinned drawing DRC report. The standalone review in `verify_review.py` checks the final GDS, exact pair sets, manifest hashes, and drawing/mask report values independently of the generator's summary counts.

KLayout connectivity is built with a flat top-cell `LayoutToNetlist`, using pinned APRtools layer rules for M1/M2/V1/GC/CO and actual v59_4 LEF pin layers. It connects M1–V1–M2 and GC–CO–M1; AP/AN transistor diffusion is intentionally excluded. All 421 placed instances match; all 987 actual signal pins are labeled, with zero missing pins and zero opens. The routed checkpoint goes from 14 short components / 143 transitive net pairs to 12 / 50. Exact set comparison shows 93 pairs removed and no new pair. The two-via stale crossings previously isolated at (753.3,600.0) and (953.1,255.1) are among the accepted deletions. The full removed-ref list, pair lists, and trial decisions are recorded in `build/manifest.json`.

The candidate retains two unrelated short components. Its official drawing report has the same two inherited `GC.ANT` markers as the composed checkpoint. Official MDP mask checking also has two inherited `WAR06: Floating SG Detected` markers at those same BUFTH locations (near x=1009.3 and 1592.5 µm); the baseline and candidate mask marker sets match exactly. The DRC wrapper returns nonzero because these reports contain items, so this is not a DRC-clean design.

Review found that the generator's `groups` field is informative but should not be used as an acceptance objective: a locally useful via deletion may split one electrical component while eliminating multiple net pairs. Acceptance is correctly based on the strict subset relation over the complete pair set, along with no opens/missing pins, unchanged rail checks, and no new drawing marker. Exact GDS instance diff confirms the output differs from its source only by the 17 listed top-level routing vias; there are no inserted instances and the top-cell bbox is unchanged.

## Reproduction and review

From the repository root:

```sh
python3 scripts/check_toolchain.py
python3 scripts/prune_route_vias.py
python3 scripts/routing_diagnostics.py \
  --gds experiments/via_prune/build/via_pruned.gds \
  --pins experiments/routed_checkpoint/build/audit/actual_pin_map.json \
  --shapes experiments/metal_repair/build/junction_y7296/net_shapes.json \
  --placement experiments/phys_desc5/layout/placement.json \
  --out experiments/via_prune/build/audit --poly \
  > experiments/via_prune/build/audit.log 2>&1
python3 scripts/run_apr.py --design-root experiments/via_prune apr/drc_pdk.py \
  "$PWD/experiments/via_prune/build/via_pruned.gds" ishi_vga_core \
  -r "$PWD/experiments/via_prune/build/drawing.lyrdb" \
  > experiments/via_prune/build/pdk_drc.log 2>&1
python3 scripts/run_apr.py --design-root experiments/via_prune apr/drc_pdk.py \
  "$PWD/experiments/via_prune/build/via_pruned.gds" ishi_vga_core \
  -r "$PWD/experiments/via_prune/build/via_pruned_mdp.lyrdb" \
  --mdp --mdp-gds "$PWD/experiments/via_prune/build/via_pruned_mask.gds"
python3 experiments/via_prune/verify_review.py
```

`build/verification.json` records source/output/script/config/audit hashes, full resolved/new pair sets, exact top-cell instance diff, and drawing/mask marker geometry. Current candidate SHA256: `bac7c0eb4b19dd017edd43a3599bb80f848d38e349cc0d5e0dedb16f854da94c`.
