# TR-1um GC jumper probe

## Result

The `poly_probe_device_array` is a DRC-clean, mask-clean geometry probe for a GC gate-poly jumper that joins two M1 endpoint islands through CO and crosses an independent M1 wire. Its 12 cases span GC lengths 10, 20, 40, and 80 µm and widths 1, 2, and 3 µm. Each endpoint connects through an M1 spur, an offset V1, and M2 to the A pin of a real v59_4 `INV_X1`. The two A pins share the jumper net; both inverter outputs remain unconnected. An independent vertical M1 line crosses the GC at its midpoint. Twelve standalone GC wire cases and four metal-only M2/V1 controls (lengths 10/20/40/80 µm) are retained in `poly_probe_array.gds`.

The device coupon passes official pinned drawing DRC with 0 violations and the official mask DRC (`run_IP62.drc`) with 0 violations. KLayout `LayoutToNetlist` extraction via pinned APRtools confirms 24 `INV_X1` instances (2 MOS devices in the master, hence 48 intentional MOS devices), exactly two inverter A pins on every bridge net, and separate bridge/crossing nets in all 12 cases. The negative controls pass: removing a GC span creates two same-name endpoint nets; inserting CO at the crossing merges the bridge and crossing labels. The standalone wire coupon passes drawing DRC and its positive/negative connectivity checks, but its mask run reports 36 `WAR06: Floating SG Detected` warnings because those wire-only GC nets do not terminate at a transistor gate. This is why the device-connected coupon is the mask-qualified result.

This is a geometry and connectivity probe, not a full LVS comparison against a circuit schematic. The wire-only coupon has no devices. The device coupon intentionally uses 24 pinned INV instances; the KLayout extraction confirms their count and A-port connectivity, but there is no independent schematic netlist for a formal compare.

## Rules and model evidence

The run is pinned to APRtools `8f6962bf2df1618d633f8a81c230fec895fc83aa`, TR-1um `f408d3b5c23a8ebe44f02b0482a9270601e2880f`, and v59_4 cell GDS/LEF/Liberty. `scripts/check_toolchain.py` passes before generation and official deck execution. No upstream files were edited.

The generator imports dimensions from pinned [`rules.py`](../../tools/APRtools/apr/rules.py): GC layer (8,1), CO (11,0), M1 (13,0), V1 (19,0), M2 (20,0), GC minimum width/space 1.0/1.2 µm, CO size 1.0 µm, M1 minimum width 1.8 µm, V1 cut 1.4 µm, M2 minimum width 3.0 µm, and DBU 0.001 µm. It parses missing enclosure values from the live [`run.drc`](../../tools/TR-1um/libs.tech/klayout/tech/drc/run.drc): CO-to-GC 0.8 µm (line 176), M1-to-CO 0.8 µm (line 252), M2-to-V1 1.0 µm (line 270), and V1-to-M1 1.0 µm (line 271). The V1s sit outside the GC/CO stack on M1 spurs; this avoids the deck's V1/GA and V1/CO restrictions. The deck's GC antenna condition is at line 363; `03_Electrical.drc` defines the floating-gate checks that feed it.

The pinned LVS extraction deck distinguishes gate-poly resistor structures using SG together with RS (`01_Extract.lvs`, “Saliside Gate Resistance”). The pinned `models_IP62_res_v5.lib` contains F_RR and F_RS models; F_RS applies to the resistor-layer structure, not the GC layer used here. The reviewed deck/model sources do not provide a qualified sheet resistance, contact resistance, or coupling-capacitance model for this GC/CO/M1/V1/M2 jumper. No RC or delay estimate is claimed.

## Reproduction

From the repository root:

```sh
python3 scripts/check_toolchain.py
python3 scripts/poly_probe.py
```

The script creates both arrays from `experiments/poly_probe/config.py`, runs the pinned official DRC through `scripts/run_apr.py`, creates official MDP GDS for each drawing-clean coupon, and records connectivity, logs, reports, and SHA-256 values under `experiments/poly_probe/build/` (the mask `.lyrdb` reports are at the experiment root). Main machine-readable results are in [`results.json`](build/results.json); extracted geometry settings are in [`geometry.json`](build/geometry.json) and [`device_geometry.json`](build/device_geometry.json).

Final artifact SHA-256 values from the recorded run:

- `poly_probe_array.gds`: `d24c1328a98c798997ffe78358342677b7d1a8418bfdd54ecad13d2b2cc4d635`
- `poly_probe_device_array.gds`: `3574b2910041741d0f769ca1a25128cc8ef5f08f50eaa9d946c6e8b00f28a413`
- `build/poly_probe_device_array_mdp.gds`: `ea845e3118d9bef89c45a2297b8c39c0f685997a7a61b6c02c83fb8f0b7d901f`
- `toolchain.lock.json`: `31f6f929b6be02cb5809d1c0d4d077f7fb7ca0eeb6c0b92d5885eeef2a4ebc5f`
- `scripts/poly_probe.py`: `5f0d96e6c36d40639c63d2782eb1898029204931bc5bd9bcbed691a2997f224b`
- `experiments/poly_probe/config.py`: `7a9b56897bb4f283ef9818e7eb1fca60437f52392bfbf6cddff518a3c2eca49b`

Source, deck, and cell-GDS hashes are also recorded in `results.json` so later runs can be compared against the exact evidence set.
