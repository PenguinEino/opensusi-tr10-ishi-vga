# maze_069 multi-component repair

## Final result

The frozen input is [`maze_073/build/candidate.gds`](../maze_073/build/candidate.gds), SHA256 `d695d2cd225ba3f2db0970f8451708a4f855979d6de2760005122af562c5355b`. The final candidate [`build/candidate.gds`](build/candidate.gds), SHA256 `07d524e0272ad8946389297de72901679101f6580e0ade9500628d7b6e5abb6f`, passed `scripts/validate_route_candidate.py --design-root experiments/maze_069` with status **ACCEPTED**.

The full actual-pin and flat-connectivity audit reduced the source from 27 short pairs to 21, removing the six pair combinations among `_069_`, `_065_`, `_161_`, and `_240_`; it introduced no pair, open, or missing pin. All 987 placed signal pins were identified on the same 421 instances before and after. VDD/VSS topology and attached signal labels were unchanged. Drawing and official mask marker sets were exact subsets of the source: both retained only the same two inherited GC.ANT / WAR06 markers.

Candidate bbox is `[-9.0, 0.0, 1777.5, 1760.3]` µm, size `1786.5 × 1760.3` µm within the configured `[1800, 1800]` µm limit. Cell hierarchy and non-top-cell inventory are unchanged; only top-level M1/M2/V1 geometry changed. The candidate is a routed repair trial; broader final integration checks are tracked separately.

## Reproduction and routing details

The reproducible settings are in [`config.py`](config.py). The design-owned implementation is [`scripts/maze_route_multicomponent.py`](../../scripts/maze_route_multicomponent.py); the exact generator snapshot used to create the accepted GDS is [`build/generator_used.py`](build/generator_used.py), SHA256 `6febd7588ad8f68c2607f02eed25388e8b81e2ee4b9e6d9798490e82510010d6`. Run from the repository root:

```sh
python3 scripts/check_toolchain.py
python3 scripts/maze_route_multicomponent.py --design-root experiments/maze_069
python3 scripts/validate_route_candidate.py --design-root experiments/maze_069
```

The cuts use distinct physical M2 boxes from route-map indices `[3,4,5,8,9,10,12,13,14,17,19,21,26,28,30,35,37,39]`. Exact coincident route-map boxes at indices `[9,18,27,36]`, `[13,22,31,40]`, and `[14,23,32,41]` are each removed at their full source multiplicity of four. The configured eleven via coordinates are verified against the input GDS and all top-level route-via instances at each listed coordinate are removed. An explicit upper-spine M2 bridge `[265.6,1257.3,269.0,1333.7]` µm keeps the four upper `_069_` pins connected while clearing `_161_`'s foreign M2 stub. Every extraction rejects any foreign pin root in a target component, and every accepted route step must strictly reduce the target-component count.

The accepted search used `local_wide`, M2-only terminal masks, 0.9 µm grid, and outer bounds `[-18.0,1.8,1773.0,1796.4]` µm. Two route steps reduced the target from three components to two, then one (872 and 3,678 path nodes; 3 and 2 vias). Per-step grid, solver, path, log, and GDS checkpoints are in `build/step_01` and `build/step_02`.

Earlier bounded attempts are retained under `build/attempt_001` through `build/attempt_003`. The two interior-bound searches connected 3→2 but found no second path. The first outer-bound route with both M1/M2 terminal masks also connected 3→2→1 but was rejected: it introduced four M1.W1, one M1.S1, and one ER0045 drawing markers (and corresponding mask markers). The final M2-terminal search avoids those new markers; its full validator result is `build/verification.json`.

## Evidence and hashes

`build/manifest.json` records the source, candidate, configuration, route inputs, exact removed/added geometry, step hashes, and final bbox. `build/verification.json` records the independent actual-pin, pair-set, power, bbox, hierarchy, drawing, and mask checks. `build/implementation_hashes.json` records the deliverable and evidence hashes. No RTL, common router, upstream tool, source GDS, or other experiment was modified for this repair.
