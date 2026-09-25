# Local maze-routing probe

This is a read-only prototype for replacing one known long M2 branch while
keeping all other routed geometry and placed-cell geometry as obstacles. It
does not change the accepted GDS, APRtools, the root design, or any existing
experiment. Run it from the repository root:

```sh
python3 scripts/check_toolchain.py
python3 scripts/maze_probe.py
```

The selected case is `_040_` against `_058_` in
`experiments/phys_desc5/build/postrepair_compacted.gds`. The branch is the
three `_040_` route-map records at x=973.0..976.4 µm, y=870.0..1369.8 µm;
each matches exactly one top-level M2 box. The route-map overlap audit had no
same-layer route-box overlap for this pair because the crossing is at an
actual cell-pin geometry. The preflight keeps recursive cell/PCell shapes in
the obstacle geometry, including shapes that intersect the three removed
route boxes. It does not use the flattened union subtraction that would erase
those unrelated obstacles.

## Candidate router architecture

The next step should use an A* graph on the existing 2.7 µm grid, in a bounded
window around the branch. Nodes carry M1/M2 layer and grid coordinates;
orthogonal steps are permitted, with cost for length and bends, and layer
transitions are V1 candidates. Obstacle checks inflate each layer's geometry
by half the candidate wire width plus that layer's minimum spacing. A V1
transition must be clear on both layers over its full cut plus the M1/M2
enclosures. Endpoint access segments remain anchored to the existing M1
trunk at (974.7, 870.0) µm and the output pin landing at (974.7, 1369.8) µm;
the final grid hop must be connected by a checked off-grid stub. Search may
detour horizontally around the row at y=964.5..1023.9 µm, then return to the
original x near the output pin. Any emitted path still needs official DRC and
actual pin-connectivity verification before it can be considered a repair.

The APRtools channel router is a multi-pass track heuristic rather than a
generic maze router. Its own route-map JSON is useful for identifying top-cell
route boxes, but does not assign ownership to via PCell instances. Therefore
this prototype produces only an obstacle/rip-up preflight and deliberately
does not write a GDS or remove vias. A production route editor should require
an explicit via ownership/retention plan and preserve all non-target instances.

## Prototype result

`preflight.json` records the source hashes, selected shape indices, exact
match counts, obstacle counts, and layer-rule values imported from pinned
`tools/APRtools/apr/rules.py`. In the configured input, the three target M2
boxes are unique. The check also detects other geometry intersecting those
boxes and leaves it present in the obstacle set. This proves safe target-box
selection, not a route, DRC, LVS, or connectivity pass.

Installed local modules checked: KLayout DB 0.30.6, Shapely 2.1.2, SciPy
1.17.1, and NetworkX 3.6.1; OR-Tools is not installed. No dependency was
installed or changed. The prototype uses standard-library JSON/path/hash
logic plus KLayout's installed API and the locked APRtools rules module.
