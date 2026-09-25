# `_173_` maze-routing attempt: no legal grid path found

The source [`maze_073` candidate](../maze_073/build/candidate.gds) is frozen at SHA256 `d695d2cd225ba3f2db0970f8451708a4f855979d6de2760005122af562c5355b`; the file remains unchanged. The trial config targets `_173_`, removes route-map M2 shapes 4, 5, 6, 8, 9, and 12 plus M1 shape 7, and deletes the four existing `via_1` instances at (240.3,1339.1), (240.3,961.8), (207.9,961.8), and (207.9,265.9) µm. Each configured shape and via was checked present in the source before the trial. No candidate GDS was emitted because the grid search found no path.

The first 0.9 µm search used the originally requested y range 100.8–1756.8 µm and exhausted its reachable graph after 1,104,550 expansions. A second 0.9 µm search extended the interior range to y=1.8–1758.6 µm and still found no path after 1,111,734 expansions. A 0.45 µm search over that full source-interior range reached the configured 4,000,000-node cap without finding a route. The final 0.45 µm search raised the configured cap to 20,000,000 and exhausted the reachable graph after 4,579,354 expansions with no path; this final result was not truncated by the node cap. The candidate attempts, grid binaries, solver logs, and per-attempt config snapshots are preserved under [`build/attempt_001`](build/attempt_001/) through [`build/attempt_004`](build/attempt_004/).

There is no physical candidate to validate, so no candidate connectivity, power, drawing DRC, or mask DRC result is claimed. The source remains at 27 short pairs and zero opens per the root-provided source audit. This no-path result is specific to the current grid masks, bounds, and two-layer maze model; it does not establish that the physical connection is impossible.

The final design settings are in [`config.py`](config.py). Reproduce the last search from the repository root with:

```sh
python3 scripts/check_toolchain.py
python3 scripts/maze_route.py --design-root experiments/maze_173
```

That command is expected to exit with `No maze path found`. [`build/no_path_report.json`](build/no_path_report.json) records the exact final configuration, source and generator hashes, and all attempt outcomes. The common generator and input GDS were not edited.
