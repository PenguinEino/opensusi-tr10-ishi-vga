# Grouped redundant-via pruning

This experiment starts from the frozen [`via_pruned.gds`](../via_prune/build/via_pruned.gds), SHA256 `bac7c0eb4b19dd017edd43a3599bb80f848d38e349cc0d5e0dedb16f854da94c`. It does not modify that source or add route geometry. The new script removes configured top-level `via_1` instances only. Connectivity uses flattened KLayout `LayoutToNetlist` across M1/M2/V1/GC/CO and actual LEF pin centers mapped to their conducting pin layer; power component counts and signal labels are checked on every trial.

The known `_048_`/`h[0]` pair was applied first by deleting `via_1$2` at (774.9,287.5) and (774.9,157.9) µm. That seed reduced transitive intended-net pairs from 50 to 49, with no opens or missing pins, unchanged VDD/VSS connectivity, and no new official drawing markers. Then neutral single-via removals were recomputed from the 14 configured locations. There were 12 eligible neutral singles in pass 0, 10 in pass 1, and 8 in pass 2. The finite search tried pairs and triples, for 182 combination trials total; it stopped after pass 2 found no acceptable improvement.

Two further groups passed all acceptance checks:

| Group | Via centers removed (µm) | Pair count | Resolved pairs |
|---|---|---:|---|
| 1 | (240.3,670.2), (240.3,567.6) | 49 → 47 | `_222_`/`_223_`; `_223_`/`_233_` |
| 2 | (1109.7,583.8), (1109.7,697.2) | 47 → 45 | `_185_`/`_247_`; `_247_`/`h[4]` |

Across the three accepted groups, the exact pair set is reduced from 50 to 45, with no added pairs. The number of mixed short components falls from 12 to 11. All 987 actual signal pins remain connected, with zero opens and zero missing pins. Power components remain one each for VDD/VSS; VDD contains only `1'h1`, and VSS has no signal net.

The final checkpoint is [`via_groups_pruned.gds`](build/via_groups_pruned.gds), SHA256 `12ec87f01645b43c4f510b6ebf9055a49c6af5ba584e7517c24e1d1b0849a341`. Its independent pin-shape M1/M2/V1/GC/CO audit is in [`final_audit/metal_connectivity.json`](build/final_audit/metal_connectivity.json). The official drawing DRC has two inherited `GC.ANT` markers and no new marker geometry; its `.lyrdb` is byte-identical to the frozen source report (SHA256 `0101693701de4cd947b0b086d91c942e8501e8ccd884acbe17d53961543a3052`). The final mask DRC has two inherited `WAR06` markers and no new markers; its report matches the frozen source mask report (SHA256 `90fb794111f5bf9cc36d628428166f09d9bedcbdfe25666707ee91f86c5e93c6`). Both reports are nonempty and the wrapper returns 1 for them; this checkpoint is an improved diagnostic result, not a DRC-clean or submission-ready layout.

All accepted and rejected trial coordinates, exact removed instances, pair diffs, pin/open/power results, official drawing marker deltas, and output hashes are in [`build/manifest.json`](build/manifest.json); complete search output is [`build/search.log`](build/search.log). Each DRC-tested improvement has its own candidate GDS and log directory. No trial edits a frozen source checkpoint.

To reproduce from the repository root:

```sh
python3 scripts/check_toolchain.py
python3 scripts/prune_via_groups.py > experiments/via_groups/build/run.log 2>&1
```

The design-owned settings, including the fixed seed pair, neutral trial locations, pair/triple sizes, pass count, and the 500-trial ceiling, are in [`config.py`](config.py). The script reuses the flattened connectivity and marker-set helpers in [`prune_route_vias.py`](../../scripts/prune_route_vias.py); it does not modify that earlier script.

Implementation and report metadata hashes are recorded separately in [`build/implementation_hashes.json`](build/implementation_hashes.json). The final output, frozen input, config, generator, reused connectivity helper, manifest, final audit, and DRC artifacts can be checked there.
