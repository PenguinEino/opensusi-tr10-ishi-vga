# Reset synchronizer constant tie

The `_542_.D` input is a literal `1'h1` in placement metadata, but the original route GDS leaves it unconnected. This experiment connects that pin to the actual VDD mesh while preserving the input GDS. The first local spur attempt is retained as `build/constant_tied_failed_v1.gds`; although its electrical rail probe passed, its official PDK DRC added one `V1.CO` violation and it is superseded.

The current `build/constant_tied.gds` uses an M2 escape from `_542_.D` to a top-channel via, an M1 bridge, and a second V1 landing on the nearest electrically probed VDD M2 strap. The geometry and measured placement are in `build/manifest.json`; `build/constant_tie_patch.json` exports the added M1/M2/V1 polygons so the repair can be applied to a later same-placement metal candidate. The route raises the top boundary to 1760.3 µm while keeping the overall 1783.8 × 1760.3 µm extent below 1800 µm.

The generator's KLayout `LayoutToNetlist` probe checks all 987 actual signal pin points against the placed VDD and VSS labels. Before the tie, neither rail contains signal nets. Afterward, VDD contains only `1'h1`; VSS remains unchanged and distinct. `scripts/routing_diagnostics.py --poly` independently reconstructs actual pins and GC/CO connectivity on the full output. Baseline and candidate both have zero opens and exactly the same 14 short components / 153 transitive short pairs: the tie creates no new opens or shorts. This does not resolve the unrelated core shorts.

The machine-readable pair-by-pair baseline comparison, with empty `new_pairs` and `resolved_pairs`, is `audit/connectivity_comparison.json`.

The official pinned PDK DRC was run through `scripts/run_apr.py` on this candidate. It reports two `GC.ANT` markers, both retained baseline BUFTH markers; the DFFRB constant-input marker is gone. The wrapper exits nonzero when its report contains violations, so exit status 1 is expected here; the report count is two, with no new marker category or location. This is not a DRC-clean core.

Reproduce the generation, full-core connectivity check, and official DRC from the repository root:

```sh
python3 scripts/check_toolchain.py
python3 scripts/route_constant_tie.py > experiments/constant_tie/build/generate.log 2>&1
python3 scripts/routing_diagnostics.py \
  --gds experiments/constant_tie/build/constant_tied.gds \
  --pins experiments/phys_desc5/build/postrepair_pins.json \
  --shapes experiments/phys_desc5/build/postrepair_shapes.json \
  --placement experiments/phys_desc5/layout/placement.json \
  --out experiments/constant_tie/audit --poly
python3 scripts/run_apr.py --design-root experiments/constant_tie apr/drc_pdk.py \
  "$PWD/experiments/constant_tie/build/constant_tied.gds" ishi_vga_core \
  -r "$PWD/experiments/constant_tie/build/constant_tied.lyrdb" \
  > experiments/constant_tie/build/pdk_drc.log 2>&1
```

The DRC report's two markers are the input Schmitt buffers `u_bufth_reset_n` and `u_bufth_clk`, as identified in [the routing audit](../routing_audit/postrepair_drc_ownership.md). The failed v1 report is also retained for comparison. `check_toolchain.py` is only a pinned-version and asset check; it does not certify DRC/LVS/STA.

Principal hashes:

| Artifact | SHA256 |
|---|---|
| immutable input `postrepair_compacted.gds` | `7ca31f07ead9b36d20af43e1a732cbf51f22ebd1290e15bbb6346c6d124846ba` |
| `build/constant_tied.gds` | `de8171290a10868912b8a5b3354dcf26bacc2918628f92679383fb890bc579c7` |
| `build/constant_tied.lyrdb` | `0101693701de4cd947b0b086d91c942e8501e8ccd884acbe17d53961543a3052` |
| failed v1 GDS | `f96d62dfae09373de6c89c322c1d5e2b19588151426215155b12a3ed70e73a47` |
| failed v1 DRC report | `64d6b83e807365f8c7d56d96927f6116fe5a041ddbbc47a04953394dbea0009c` |
| `scripts/route_constant_tie.py` | `b570c9e0f561696e32689d42237dae284073c1e08f00d0860ccada8ee8764e74` |
| `config.py` | `b75766770a3608f09d3e2c4e7da8ac4e67f5b443eeafa41cfdeb0b812667220f` |
| `build/constant_tie_patch.json` | `ccc2fd5803ddb27a0000f7c3a5dcfe16d99f09621a8e3ec3511000e4a4e65da3` |
| `audit/metal_connectivity.json` | `013ae5c89edb945a457c18c1b965f6a3f2f8f1996588c8fd849b63c03a74c74e` |
