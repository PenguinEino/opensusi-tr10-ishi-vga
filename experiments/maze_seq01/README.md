# Sequential route checkpoint 01

Reruns the `_162_` maze on validated seq00, source SHA256 `ddedcb9c8b9729407531ad0d15b875d4e3453096d85f6c23a9216d59ef1066c7`, including the original terminal extension. The new candidate is `c7072d9da9b51bbf106fa7af7a25b66bb6b4ae97d858fc45efb2d72f9ec246ce` (3,098 path nodes, 3 vias; bbox unchanged). Pair count falls 15→12, resolving `_033_`–`_162_`, `_038_`–`_162_`, and `_162_`–`hsync`, with no new pairs. The common validator reports ACCEPTED with no opens/missing pins, unchanged rails, and drawing/MDP marker subsets. See `build/manifest.json` and `build/verification.json` for input hashes and full pairsets.

Reproduce with `python3 scripts/check_toolchain.py`, `python3 scripts/maze_route.py --design-root experiments/maze_seq01`, then `.venv/bin/python scripts/validate_route_candidate.py --design-root experiments/maze_seq01`.
