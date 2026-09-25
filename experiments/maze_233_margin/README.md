# maze_233_margin

This isolated candidate removes the `_222_` / `_233_` short from the frozen
`maze_209_fix` source by rerouting the target net through the available left
margin. The candidate is electrically and DRC validated by
`scripts/validate_route_candidate.py`.

The source bbox is `[-6.3, 0.0, 1777.5, 1760.3] µm`; the candidate bbox is
`[-9.0, 0.0, 1777.5, 1760.3] µm`. The candidate therefore grows 2.7 µm to the
left and has a bbox size of `1786.5 × 1760.3 µm`, within the explicit
`1800 × 1800 µm` limit in `config.py`. This is a bounded-size result; it does
not establish fit within any particular frame or package outline.

Validation status: **ACCEPTED**. The full short-pair set decreases from 21 to
20 with no new pairs; all 421 placed instances and 987 signal pins are
matched, with zero opens or missing pins. Power topology and cell hierarchy
are unchanged. Official drawing and mask DRC each retain the same two markers
as the frozen source (no added markers).

Reproduce with:

```sh
python3 scripts/check_toolchain.py
.venv/bin/python scripts/maze_route.py --design-root experiments/maze_233_margin
.venv/bin/python scripts/validate_route_candidate.py --design-root experiments/maze_233_margin
```

Artifact hashes:

- Source GDS: `723bf30d9cf8d92e0804b818176cb39b58dda27f153160dc8cd293e610b8446e`
- Candidate GDS: `85aaa5ab3b1c51ca7cc2ab18ede2d4c3582a5023557451be9b8c527352b97d3e`
- Config: `cf2b5ca453f5558a4024e28b40630684734747c0157a47adda082d02126f1cd2`
- Validator: `8e033c8f6287a9c47050bdfd519c37176933fb1687ac89408f1b3c996b09648e`
- Verification payload: `29c25163583ed17113620eb939e02643a5ae4d64191a35e1372a6c868adacfe7`

Detailed evidence is in `build/verification.json` and the per-check audit and
DRC artifacts under `build/`.
