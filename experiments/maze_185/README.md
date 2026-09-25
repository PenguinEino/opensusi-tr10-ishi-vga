# `_185_` / h[4] local maze-route trial

This experiment starts from the frozen, validated composed checkpoint `experiments/maze_combined/build/candidate.gds` (SHA256 `862a7d9279362ecfeee9a7dcdc02f209c7d7be15111bdf30bfbc4499d744b818`). It removes `_185_` map boxes 4, 5, 8, and 12 (the duplicate boxes at indices 5 and 12 are each removed twice) plus top-level `via_1$2` instances at (990.9,751.2), (990.9,1268.9), and (990.9,1279.7) µm. The exact-two-pure-components precondition passed.

The first `all_wide` search and the authorized `local_wide` search both found no path with the original margins; their configs, logs, grids, and solver output are preserved in `build/attempt_all_wide/` and `build/attempt_local_wide/`. After widening search bounds to x=[-18.0,1773.0], y=[1.8,1796.4] µm, `local_wide` found a 3,675-node path using seven new V1s. The resulting bbox is `[-9.0,0.0,1777.5,1760.3]` µm (1786.5×1760.3), within the explicit 1800×1800 µm size budget. The bbox grows 2.7 µm at its left edge; it is not unchanged.

The common route-candidate validator reports `ACCEPTED`. It matched all 421 placed instances and 987 actual pins, with no missing pins or opens. Exact short-pair count improves 25→24; `_185_`–`h[4]` is the only resolved pair, with no new pairs. Full GC/CO-aware pin geometry and flat extraction agree. VDD and VSS remain separate single components; only VDD carries `1'h1`. Cell hierarchy and non-top cell geometry remain unchanged, and only top-level routing layers changed.

Official drawing and actual MDP mask marker sets are unchanged from `maze_combined`: two inherited BUFTH markers in each run (`GC.ANT` drawing, `WAR06: Floating SG Detected` mask, near x=1009.3 and 1592.5 µm). Their wrappers return nonzero because the reports remain nonempty. This trial adds no markers; circuit LVS and timing signoff were not run.

Candidate SHA256: `9f1d995c6c3a786fe853ab6e292467bdaf6927b35d5be34cc457b6ee52075222`. The build manifest binds the source, config, generator/solver, route-map and pin/placement inputs, pinned rules/deck, and the final grid/path hashes. The final machine-readable validation is `build/verification.json`.

## Reproduction

```sh
python3 scripts/check_toolchain.py
python3 scripts/maze_route.py --design-root experiments/maze_185 \
  > experiments/maze_185/build_expanded.log 2>&1
.venv/bin/python scripts/validate_route_candidate.py --design-root experiments/maze_185
```
