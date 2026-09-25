# Logic experiment handoff (2026-09-25)

Root/logic agent stopped new work at the requested model handoff. Root RTL/config/dependencies are unchanged. Own code is `scripts/logic_*.py` and `experiments/logic_*` only.

## Results from actual pinned `syn/syn.sh`

All entries below passed exhaustive 65,536 h/y coordinate equivalence against the current B RTL. All entries completed RTL and mapped-gate full-frame comparison at 6.30 and 6.45 MHz (315,017 ticks each), including asynchronous stopped-clock reset and release.

| Variant | Cells | Cell area um² |
|---|---:|---:|
| Current B reference | 375 | 495252 |
| logic_direct_bounds | 367 | 495572 |
| logic_direct_masked | 339 | 474403 |
| logic_espresso_colors | 533 | 690595 |
| logic_espresso_rgb | 908 | 1164997 |
| logic_factor_x | 345 | 476648 |
| logic_factor_y | 346 | 484347 |
| logic_axis_sop | 345 | 481459 |
| logic_axis_pos | 330 | 470554 |
| logic_axis_mixed | 373 | 505516 |
| **logic_bdd_yx_msb** | **339** | **466063** |
| logic_bdd_xy_msb | 478 | 658200 |

All numbers include the two input BUFTH cells and the same counter/core. Results are synthesis and pre-route STA only, NOT routed area/DRC/LVS/PEX. Full log per candidate: `build/synthesis.log`, `out/SYN_RESULTS.txt`, `out/STA_ishi_vga_core.txt`. Verified results and exact source hashes: `build/metrics.json` and `build/verification.log`.

Best candidate for small cell area is BDD with Y MSB-first followed by X MSB-first (`logic_bdd_yx_msb`). `logic_axis_pos` has fewer cells (330 vs 339) and may route better. Direct masked form is easy to combine with coordinate offsets.

## What was tried

- Direct RGB bit expressions exploiting exact palette and paint priority instead of a priority RGB mux. Define dark=color4 & ~red and purple=color5 & ~red, then output individual complements.
- Aligned binary cubes for coordinate ranges (dyadic masks) instead of magnitude comparison operators.
- Global 2D Espresso minimization of all five color masks or five nonconstant RGB bits. Both became much worse: flattened SOP loses the useful geometry factoring.
- Factoring geometry by identical X intervals or identical Y intervals.
- Espresso only for eight-input coordinate-range functions. POS means minimize the complement and invert, retaining 2D geometry factoring. This improved modestly.
- Shared reduced BDD per RGB output, same unique-node pool for all bits. Y-first 184 nodes maps better than X-first 323 nodes. Additional generated but NOT synthesized: `logic_bdd_interleaved_msb` 584 nodes, `logic_bdd_xy_lsb` 411 nodes, `logic_bdd_interleaved_lsb` 1245 nodes.

## Reproduce

`pyeda==0.29.0` was installed without changing shared Python environments:

```sh
python3 -m pip install --target .tools/logic_pyeda pyeda==0.29.0
python3 scripts/check_toolchain.py
python3 scripts/logic_generate.py
python3 scripts/logic_axis.py
python3 scripts/logic_bdd.py
python3 scripts/logic_test.py logic_bdd_yx_msb logic_axis_pos logic_direct_masked
```

`logic_test.py` executes the same approved upstream `scripts/run_apr.py --design-root ... syn/syn.sh`. It also independently runs the exhaustive coordinate test and full-frame tests. It does not regenerate or overwrite shared tests/expected_frame.hex. All experiments have a read-only-in-practice symlink `tests -> ../../tests` because the upstream testbench reads that file relative to cwd.

## Generated combination candidates, NOT run

The architecture agent reported `arch_offset_hm48` = 324 cells / 451949 um² and `arch_offset_hm56` = 327 / 453234. Combining offset counters with the above direct/masked/axis expressions may improve further.

`python3 scripts/logic_combine.py` already generated these six exact-coordinate candidates:

- logic_combo_hm48_masked
- logic_combo_hm48_pos
- logic_combo_hm48_sop
- logic_combo_hm56_masked
- logic_combo_hm56_pos
- logic_combo_hm56_sop

**These six have not even run equivalence yet.** Core RTL is snapshotted from the matching `arch_offset_*` design. Config points to each candidate's own core. Each has `offset.json`; `logic_test.py` uses it to offset the exhaustive reference coordinates and detects local core RTL for frame tests. The same 65,536 coordinates must pass after adjusting coordinates; rendered frame must still exactly match current B.

Next command after root review, if desired:

```sh
python3 scripts/logic_test.py logic_combo_hm48_masked logic_combo_hm48_pos logic_combo_hm48_sop
```

Root should own combining with the final best architecture / vertical offset candidate. `logic_combine.py` currently only snapshots horizontal -48 and -56 with vertical zero.

## Processes at handoff

- First six-candidate batch: exec session 23363 had completed by the final process inspection.
- Second batch: exec session 84667, shell PID 249155, Python PID 249156. At inspection it was in final candidate `logic_bdd_xy_msb`, gate frame tests, child vvp PID 259165. No further variants queued after this. It should finish naturally within seconds; do not launch a competing run in that candidate until it exits. Log: `experiments/logic_axis_sop/build/batch.log`.
- Final poll: both sessions 23363 and 84667 exited with code 0. All 11 tested candidates are complete; no logic-agent process remains.

## Caveats for future reviewer

Generated logic experiment config imports root config by `runpy` and preserves current design-root resolution, then overrides SYN_RTL with absolute source paths. Existing tests and upstream paths are pinned. The generators have implicit shared source dependence on current B asset and current root core; source hashes in metrics record actual tested inputs. Do not mistake generated but untested candidates for completed ones.

A first attempt at converting complement-of-geometry directly to DNF was killed due to expansion, then replaced by exact raster run construction. No output from that abandoned expansion was used in the verified candidates. All completed candidates were verified against the current B for all 65,536 coordinates, including outside active screen.
