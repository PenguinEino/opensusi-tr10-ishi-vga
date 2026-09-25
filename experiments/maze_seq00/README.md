# Sequential route checkpoint 00

Replays the independently validated `maze_h1` and `maze_193` edits onto frozen `maze_194` (source SHA256 `08f63ce0f800564c3d7c1b90ff1f9a39a9ac20de5da23b276b93863fbdbc132a`). The candidate SHA256 is `ddedcb9c8b9729407531ad0d15b875d4e3453096d85f6c23a9216d59ef1066c7`. Pair count falls 17→15, resolving `_000_[1]`–`_193_` and `_068_`–`h[1]`, with no new pairs. The common validator reports ACCEPTED: no opens/missing pins, rails unchanged, and drawing/MDP markers are subsets of baseline. Replay details and hashes are in `build/manifest.json`; full checks are in `build/verification.json`.

Reproduce with `python3 scripts/compose_route_patches.py --design-root experiments/maze_seq00` followed by `.venv/bin/python scripts/validate_route_candidate.py --design-root experiments/maze_seq00`.
