# maze_173_margin

Isolated margin-route prototype for `_173_`, generated from the frozen
`experiments/maze_073/build/candidate.gds` source. It removes the configured
seven route boxes (M1/M2) and only the two vias at `(240.3, 961.8)` and
`(207.9, 961.8)` µm, then connects the extracted target components with a
3-via M1/M2 maze path. The other two endpoint vias in the regular trial were
left in place.

The full candidate validator reports **ACCEPTED relative to this source**:
27 short pairs became 26, removing only `(_108_, _173_)`; no new pairs,
missing pins, or opens were found. All 421 instances and 987 signal pins
matched. VDD/VSS topology, hierarchy, non-top-cell inventory, and allowed
top-level routing-layer scope remained unchanged. Official drawing and MDP
reports each retain the same two markers as the configured baseline.

The route uses the available left margin. Bbox changed from
`[-6.3, 0.0, 1777.5, 1760.3]` to `[-9.0, 0.0, 1777.5, 1760.3]` µm,
with a 2.7 µm extension at the left edge. The `1786.5 × 1760.3` µm bbox is
within the explicit `1800 × 1800` µm experiment budget; this does not prove
fit to a frame or package outline. The route's outer left track is centered
at x = -8.1 µm. Do not merge this candidate blindly with another branch that
uses the same margin; the route must be regenerated and checked against the
final clean ancestor.

Reproduce from this experiment config:

```sh
python3 scripts/check_toolchain.py
.venv/bin/python scripts/maze_route.py --design-root experiments/maze_173_margin
.venv/bin/python scripts/validate_route_candidate.py --design-root experiments/maze_173_margin
```

Key hashes:

- Source GDS: `d695d2cd225ba3f2db0970f8451708a4f855979d6de2760005122af562c5355b`
- Candidate GDS: `e0cbb75b2e61a59e75a8d99195469d2202aa5a549d933366de4c58d5a29c76b6`
- Config: `21e2a118b488191f7310b65fb99ee01f980509b0883727bd5596f3e348ad6109`
- Generator: `86166322dca4bc51e89cb629ab0e3a404925f46e977a6558a318d9d49016d996`
- Solver: `139fc9eeffcd383ac5067c1350233939a86f64c64ff998582ef849f96a146dc9`
- Verification payload: `f24d5548c26adae035aee48543f480af82eed3039943cb3188790d9550a27f7e`

The detailed verification, manifest, and official reports are under `build/`.
