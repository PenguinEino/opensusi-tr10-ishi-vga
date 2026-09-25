# Composed maze-route trial

This experiment replays two independently generated route edits (`maze_h1` and `maze_193`) onto the frozen `maze_073` candidate (input SHA256 `d695d2cd225ba3f2db0970f8451708a4f855979d6de2760005122af562c5355b`). The design-owned composer binds each patch's manifest and GDS by SHA256, verifies the patch's own source→candidate raw M1/M2/V1 box and via-instance delta against its manifest, then replays only exact top-cell boxes and exact top-level via cell/transforms. It rejects absent or ambiguous delete geometry. It does not flatten, alter, or subtract geometry in nested cells.

The final candidate SHA256 is `862a7d9279362ecfeee9a7dcdc02f209c7d7be15111bdf30bfbc4499d744b818`. The compose manifest records both patch source/candidate/manifest hashes and the combined six removed M2 boxes, four route vias, and seventeen added M1/M2/V1 boxes. The write is timestamp-free. The base GDS and both patch experiments remain untouched.

The common validator reports `ACCEPTED`: 421 placed instances and all 987 actual pins matched; zero missing pins and opens; short pairs decreased from 27 to 25 with no new pair. The resolved pairs are `_000_[1]`–`_193_` and `_068_`–`h[1]`. Flat connectivity agrees with the full GC/CO-aware pin-shape audit. VDD and VSS remain separate single components; only VDD connects to `1'h1`. Bbox and standard-cell hierarchy are unchanged, and only top routing metal layers changed.

Official drawing and actual MDP mask marker sets are both exact matches to their baselines: two inherited BUFTH markers (drawing `GC.ANT`; mask `WAR06: Floating SG Detected`, around x=1009.3 and 1592.5 µm). The DRC commands return nonzero because those reports remain nonempty. This does not claim a DRC-clean design, circuit LVS, or timing signoff.

## Reproduction

From the repository root:

```sh
python3 scripts/check_toolchain.py
python3 scripts/compose_route_patches.py --design-root experiments/maze_combined
.venv/bin/python scripts/validate_route_candidate.py --design-root experiments/maze_combined
```

The composer writes `build/manifest.json`; the validator writes `build/verification.json`, both with current input and source hashes. The validation log and official reports are preserved in `build/`.
