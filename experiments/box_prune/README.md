# Exact route-box pruning trial

This trial starts from the frozen via-pruned GDS and never rewrites that
source. Settings, including its SHA256, are in `config.py`; the generator is
`scripts/prune_route_boxes.py`. Run from the repository root with:

```sh
python3 scripts/check_toolchain.py
python3 scripts/prune_route_boxes.py --preflight-only
python3 scripts/prune_route_boxes.py
```

The search groups identical top-level M1/M2 boxes, using route-map overlaps
with current short-pair nets and boxes near their actual pins to prioritize
candidates. It deletes only those exact top-level rectangle groups; it never
subtracts from a flattened region, so cell/PCell pin geometry is preserved.
Each trial uses actual-pin connectivity. Acceptance requires a strict subset
of the prior short-pair set, no opens or missing pins, unchanged power
component counts and VDD/VSS signal labels, and official drawing DRC markers
that are a subset of the immediately preceding accepted layout.

## Result

The pinned toolchain check passed. The frozen input was
`experiments/via_prune/build/via_pruned.gds`, SHA256
`bac7c0eb4b19dd017edd43a3599bb80f848d38e349cc0d5e0dedb16f854da94c`, with
50 short pairs and no opens/missing pins. Source drawing DRC reported the two
existing `GC.ANT` markers.

The read-only preflight found 212 exact-box candidates. The full fast
connectivity scan found nine individual deletions that strictly reduced the
short-pair count, but every one opened the net whose box was deleted. The
remaining candidates did not strictly reduce the pair set. Thus no candidate
qualified for DRC acceptance, and the output
`build/box_pruned.gds` is byte-identical to the frozen source. The 212-trial
connectivity results and source hashes are in `build/manifest.json`; the
source DRC log/report are `build/source_drawing.log` and
`build/source_drawing.lyrdb`.

This result rules out whole-box deletion for the scanned candidates on this
source. It does not rule out segment-level edits, a maze reroute, or combined
multi-edit proposals; those require different candidates and independent
verification.
