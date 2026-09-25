# Maze route for `_193_`

The route starts from frozen [`maze_040` candidate](../maze_040/build/candidate.gds), SHA256 `14c35652d06558e3526dd8df401fd7d364b5721f6e0c5d46b4f24846ca4a5023`. The source file was not changed. Configuration removes `_193_` M2 shape indices 2, 3, and 4 from the route-shape map, deletes the existing `via_1$2` instances at (1725.3,616.2) and (1725.3,1025.9) µm, then searches a 0.9 µm grid bounded by `[-4.5,500.4,1773.0,1404.0]` µm. The router found a 552-node path with two vias. The exact removed boxes, added M1/M2/V1 rectangles, and hashes are recorded in [`build/manifest.json`](build/manifest.json).

The candidate is [`candidate.gds`](build/candidate.gds), SHA256 `ee28be1a738876b5bc915106b0d201f5d2ac5534345d66ee341897ca4a2ff902`. Independent actual-pin shape audit and flattened L2N agree that short pairs fall from 44 to 43, resolving only `('_000_[1]', '_193_')`; no new pair is introduced. All 987 signal pins remain present, with zero opens and zero missing pins. VDD/VSS component counts and attached signal labels match the source. The bbox, standard-cell placement, and nonrouting geometry are unchanged.

Official drawing DRC reports the same two inherited `GC.ANT` markers as the source; the source and candidate `.lyrdb` hashes both equal `0101693701de4cd947b0b086d91c942e8501e8ccd884acbe17d53961543a3052`. Official mask DRC reports the same two inherited `WAR06` markers; the actual source and candidate MDP reports both hash to `90fb794111f5bf9cc36d628428166f09d9bedcbdfe25666707ee91f86c5e93c6`. There are no new drawing or mask markers. The full checks are recorded in [`verification_summary.json`](build/verification_summary.json), with exact mask marker comparison in [`mask_validation.json`](build/mask_validation.json).

One reporting defect in the shared validator is documented for accuracy: its `--mdp` run writes the real MDP report as `candidate_mdp.lyrdb`, while the validator's mask comparison reads `candidate_mask.lyrdb`, the drawing-deck report. I preserved its original output at [`verification.json`](build/verification.json) and separately compared the actual source/candidate MDP XML marker sets and logs; both actual reports are identical and contain two `WAR06` markers.

Reproduce from the repository root:

```sh
python3 scripts/check_toolchain.py
python3 scripts/maze_route.py --design-root experiments/maze_193
python3 scripts/validate_route_candidate.py --design-root experiments/maze_193
```

The route settings are in [`config.py`](config.py). Implementation, input, output, audit, DRC, and report hashes are listed in [`build/implementation_hashes.json`](build/implementation_hashes.json). This is an improved diagnostic candidate, not a DRC-clean final layout.
