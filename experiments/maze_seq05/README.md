# Sequential route checkpoint 05

Input is the ACCEPTED `maze_seq04` candidate (SHA256 `3c831672669d10d01c57b957bbde96e9be1ce1fb7e3f8e71989950669184ac33`). This reroutes `_173_` using `maze_173_margin` route geometry settings; it does not merge an independent candidate.

Reproduce with:

```sh
python3 scripts/check_toolchain.py
.venv/bin/python scripts/maze_route.py --design-root experiments/maze_seq05
.venv/bin/python scripts/validate_route_candidate.py --design-root experiments/maze_seq05
```

Accepted candidate SHA256: `6c746d7371f78b0b5b0287054d23e3f53a8b094353499077e9eacaa34b4d47a4`. Full verification is in `build/verification.json`: 7→6 pairs, no opens/missing pins/new pairs, unchanged power and hierarchy, bbox `[-16.2, 0.0, 1777.5, 1760.3]`, and drawing/MDP marker subsets both pass.
