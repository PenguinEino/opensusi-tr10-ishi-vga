# `_162_` isolated maze-route trial

This experiment starts from the frozen `_073_` candidate and removes only
`_162_` route-map rectangles 2, 3, and 4 plus the two configured top-level
route vias. Its configuration is in `config.py`; the shared maze generator is
invoked without modification:

```sh
python3 scripts/check_toolchain.py
.venv/bin/python scripts/maze_route.py --design-root experiments/maze_162
python3 scripts/check_toolchain.py
.venv/bin/python scripts/validate_route_candidate.py --design-root experiments/maze_162
```

## Result

The frozen source is `experiments/maze_073/build/candidate.gds`, SHA256
`d695d2cd225ba3f2db0970f8451708a4f855979d6de2760005122af562c5355b`.
The 0.9 µm-grid search found a 1,275-node path using three vias. The actual
pin-shape/GC/CO audit and independent flat connectivity validation both report
27→23 unintended net pairs, with no new pairs, opens, or missing pins. The
four removed pairs are `_033_`/`_162_`, `_038_`/`_162_`, `_162_`/`_194_`, and
`_162_`/`hsync`. All 421 placed instances and 987 signal pins remain matched;
VDD/VSS component counts and attached signal labels, top bbox, stdcell
hierarchy, and non-top cell shapes/child instances are unchanged.

The initial route had two new `M1.W1` drawing markers where the existing
terminal centerline at y=292.9 µm met the grid path at y=293.4 µm. The
experiment config adds an explicit orthogonal M1 centerline extension from
(1239.3, 292.9) to (1241.1, 292.9) µm, with width generated from the pinned
M1 minimum-width rule. The rerun passed: candidate drawing and mask reports
each contain only the same two baseline markers as `via_groups`; neither
adds markers. No DRC rule was waived.

The generated GDS SHA256 is
`18b57b3297a8981af0af6d20912cab59888f09d3ebe19f3005efd6a553132e69`.
`build/manifest.json` records removed/added geometry and generator/config
hashes. `build/verification.json` records the independent audit, connectivity,
power, hierarchy, drawing/MDP results, and payload SHA256
`8ac061198812eafac5146333fdbfb432d19ffdccc25f4105046c9eef2f8700fb`.
The validator uses separate copies/reports under this build directory and
does not overwrite the input candidate.
