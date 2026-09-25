# Sequential route checkpoint 03

Input is the ACCEPTED `maze_seq02` candidate (SHA256 `4b378b730022f1c04dbb23ebb6e6b3314d54e7bcc7f0ff20edb0f8c20784dfc3`). This reroutes `_185_` only. Initial route had correct 9→8 connectivity but failed drawing and mask DRC with an M2 spacing violation at the new via pad near (689.4, 760.5). That failed evidence is preserved under `attempt_local_wide/`.

The accepted config adds an explicit same-net M2 terminal extension from (689.4, 760.5) to existing `_185_` M2 at (693.9, 760.5), joining a 1.1 µm same-net gap that DRC otherwise flagged. The route remains a single target net and introduces no foreign connection.

Reproduce with:

```sh
python3 scripts/check_toolchain.py
.venv/bin/python scripts/maze_route.py --design-root experiments/maze_seq03
.venv/bin/python scripts/validate_route_candidate.py --design-root experiments/maze_seq03
```

Accepted candidate SHA256: `2befcb5f6a2c2923d7d691db287636646ba5af2c31e13e1b2db2389916652900`. Full verification is in `build/verification.json`: 9→8 pairs, no opens/missing pins/new pairs, unchanged power and hierarchy, bbox `[-11.6, 0.0, 1777.5, 1760.3]`, and drawing/MDP marker subsets both pass.
