# Composed routed checkpoint

This directory applies the reviewed `_542_.D` constant-high tie to the accepted `junction_y7296` metal-repair checkpoint. The input checkpoint remains immutable. The exact M1/M2/V1 route polygons come from `experiments/constant_tie/build/constant_tie_patch.json`; that file exports polygon vertices, including the concave M1 bridge, and records the baseline geometry hash it was designed against.

The composition script checks hashes and compares the placed GDS instances against both the original placement and the accepted metal edit manifest. The only instance-placement delta from the original GDS is the two `via_1$2` routing vias already accepted in `junction_y7296`, moved from y=708.0 to y=729.6 µm. All other 2,219 instance references match. Applying the tie changes only top-cell M1/M2/V1 polygons.

## Verification

The actual-pin rail probe checked all 987 signal pins. Before the patch, neither rail included a signal net. Afterward VDD contains only `1'h1`, while VSS remains unchanged and separate. Independent full-core M1/M2/V1/GC/CO connectivity found all 987 actual LEF pins, zero opens, 14 short components and the same exact 143 short-pair set as the accepted metal checkpoint; `new_short_pairs` and `resolved_short_pairs` are empty in `build/verification.json`.

The official pinned drawing deck reports two inherited `GC.ANT` markers, both in the input BUFTH cells. The constant-input DFFRB marker is gone. Official `--mdp` mask generation reports two `WAR06: Floating SG Detected` markers at those same BUFTH locations; the input checkpoint had three. Both reports are strict subsets of the baseline marker polygons, with no new categories or coordinates. The wrappers return nonzero because these reports are nonempty; this checkpoint is improved but not DRC-clean. Unrelated signal short components remain.

## Reproduction

Run from the repository root:

```sh
python3 scripts/check_toolchain.py
python3 scripts/apply_constant_tie_checkpoint.py \
  > experiments/routed_checkpoint/build/apply.log 2>&1
python3 scripts/routing_diagnostics.py \
  --gds experiments/routed_checkpoint/build/routed_checkpoint.gds \
  --pins experiments/metal_repair/build/junction_y7296/actual_pin_map.json \
  --shapes experiments/metal_repair/build/junction_y7296/net_shapes.json \
  --placement experiments/phys_desc5/layout/placement.json \
  --out experiments/routed_checkpoint/build/audit --poly \
  > experiments/routed_checkpoint/build/connectivity.log 2>&1
python3 scripts/run_apr.py --design-root experiments/routed_checkpoint apr/drc_pdk.py \
  "$PWD/experiments/routed_checkpoint/build/routed_checkpoint.gds" ishi_vga_core \
  -r "$PWD/experiments/routed_checkpoint/build/routed_checkpoint.drc.lyrdb" \
  > experiments/routed_checkpoint/build/drawing_drc.log 2>&1
python3 scripts/run_apr.py --design-root experiments/routed_checkpoint apr/drc_pdk.py \
  "$PWD/experiments/routed_checkpoint/build/routed_checkpoint.gds" ishi_vga_core \
  -r "$PWD/experiments/routed_checkpoint/build/routed_checkpoint_mdp_drawing.drc.lyrdb" \
  --mdp --mdp-gds "$PWD/experiments/routed_checkpoint/build/routed_checkpoint_mdp.gds" \
  > experiments/routed_checkpoint/build/mask_drc.log 2>&1
python3 scripts/verify_routed_checkpoint.py
```

The final machine-readable summary is `build/verification.json`; `build/manifest.json` captures generator, source, patch, config, toolchain, and updated routing-diagnostics hashes. `config.py` identifies the accepted input checkpoint and reference baseline.

## Principal hashes

| Artifact | SHA256 |
|---|---|
| accepted `junction_y7296/candidate.gds` | `6f611af77ff390a34d08b3d437b32d06895eae671a9a7bea708d7bc64fef352b` |
| exact constant-tie patch | `ccc2fd5803ddb27a0000f7c3a5dcfe16d99f09621a8e3ec3511000e4a4e65da3` |
| composed `build/routed_checkpoint.gds` | `9653d8a5b6a9aba7d696e9b881a98042cc749457260c531f3f7ea33b08da7634` |
| drawing report | `0101693701de4cd947b0b086d91c942e8501e8ccd884acbe17d53961543a3052` |
| mask report | `90fb794111f5bf9cc36d628428166f09d9bedcbdfe25666707ee91f86c5e93c6` |
| mask GDS | `a1e2a3801ea141abfec4a92a66a4106bce4f9ee531d03eb474f522f219ce1e12` |
| `scripts/apply_constant_tie_checkpoint.py` | `753234b551d603b97eb2bd1a941e5fcccb0a0e2db73e64fba3b7f2b23211eb08` |
| `scripts/verify_routed_checkpoint.py` | `9e5f39656f9cc83ccefdb59ab1062e5c54cd5455901aa94fb6b0a93ffa804c2b` |
| `build/verification.json` | `ac0cea59bc14f90091367f9d727e195f8bebc8bca3667599ddefa94f802bef61` |
| `scripts/routing_diagnostics.py` | `fe34975847ee7a4d246963b622f5e11c005829128c037e30d2dbce4e1f97acb0` |
