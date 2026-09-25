# maze_173 local-wide M1 spacing trial

This isolated trial uses the frozen `maze_073` candidate as input (SHA256 `d695d2cd225ba3f2db0970f8451708a4f855979d6de2760005122af562c5355b`). It targets `_173_` with the same shape/via removals as `maze_173`, and full interior bounds `[-4.5, 1.8, 1773.0, 1758.6]` µm. The only generator feature change is `m1_spacing_mode: local_wide`, which applies ordinary M1 spacing generally and the pinned wide-M1 spacing around wide-M1 geometry. The common generator's default remains unchanged.

Two searches were performed and preserved under `build/attempt_001` and `build/attempt_002`. With a 0.9 µm grid, the search exhausted its reachable graph after 1,198,995 expansions with no path. With a 0.45 µm grid and a 20,000,000-node cap, it exhausted its reachable graph after 4,865,833 expansions with no path. Both runs used full bounds and `local_wide`; neither was cap-truncated. No candidate GDS was emitted, so no connectivity, power, drawing DRC, or mask DRC result is claimed. This result is limited to the current two-layer grid router and masks.

Reproduce either attempt from the repository root by copying the corresponding `build/attempt_NNN/config.py` over `config.py`, then running:

```sh
python3 scripts/check_toolchain.py
python3 scripts/maze_route.py --design-root experiments/maze_173_regular
```

The final `config.py` matches the 0.45 µm attempt. Per-attempt grids, solver binaries, search logs, and configs are retained; the source GDS and prior `maze_173` experiment were not modified.
