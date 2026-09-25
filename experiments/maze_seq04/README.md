# Sequential route checkpoint 04

Input is the ACCEPTED `maze_seq03` candidate (SHA256 `2befcb5f6a2c2923d7d691db287636646ba5af2c31e13e1b2db2389916652900`). This reroutes `_233_` using the bounds and local-wide M1 spacing settings from `maze_233_margin`; it does not merge the independent candidate.

Reproduce with:

```sh
python3 scripts/check_toolchain.py
.venv/bin/python scripts/maze_route.py --design-root experiments/maze_seq04
.venv/bin/python scripts/validate_route_candidate.py --design-root experiments/maze_seq04
```

Accepted candidate SHA256: `3c831672669d10d01c57b957bbde96e9be1ce1fb7e3f8e71989950669184ac33`. Full verification is in `build/verification.json`: 8→7 pairs, no opens/missing pins/new pairs, unchanged power and hierarchy, bbox `[-12.6, 0.0, 1777.5, 1760.3]`, and drawing/MDP marker subsets both pass.
