# Routing connectivity audit

This audit compares the physical connectivity of the routed `phys_desc5` baseline with the independently generated GC/CO poly-core trial. It reconstructs actual signal pins from the placed GDS instances and pinned v59_4 LEF, then unions flattened M1/M2 polygons through V1. The `--poly` mode additionally connects GC to M1 only through CO; AP/AN are intentionally omitted so gate crossings do not join source/drain diffusion. Results are diagnostic evidence for routing repair, not LVS or a substitute for the official PDK DRC.

## Results

| Input | Short components | Transitive intended-net pairs in those components | Direct route-map overlap pairs | Open nets | Missing actual LEF pins | Unlocated route-map shapes |
|---|---:|---:|---:|---:|---:|---:|
| `phys_desc5/build/postrepair_compacted.gds` (M1/M2/V1) | 14 | 153 | 24 | 0 | 0 of 987 | 1 |
| `poly_core/build/poly_core_trial.gds` (M1/M2/V1/GC/CO) | 14 | 143 | 23 | 0 | 0 of 987 | 1 |

The poly trial reduces the transitive short-pair count by ten while keeping all 987 actual placement signal pins represented and leaving the number of connected short components at 14. Full group membership, merged-geometry bounding boxes, map-layer overlap rectangles, nearby actual pins, V1 locations, and component pin geometry are in the JSON reports. Where a group has no route-map rectangle overlap, its short is still established by actual merged metal/via geometry and the report gives its full actual pin set. One route-map rectangle in each input has no physical metal at its center; examples are recorded in the JSON. This audit reports opens from the actual placed pins' component roots; it found none.

### Pin-map coverage

The GDS contains 421 placed instances (282 logic and 139 TAP/FILL), all matched to placement rows and v59_4 LEF cell types. The placement has 987 signal-pin keys, all 987 have physical LEF pin geometry found in the GDS. The older route pin map has 1,017 point records, representing 976 unique `(instance,pin)` keys: 41 records are duplicate keys, and 11 actual signal pins are absent from that map (eight RGB/HS/VS output pins, two BUFTH inputs, and `_542_.D`, the constant-high input). These omissions do not remove pins from this audit because labels come from placement metadata plus LEF geometry. All 1,017 old points land on the same physical component as their named pin; they are route anchors, not necessarily terminal coordinates. The reported nearest-LEF-rectangle distances are descriptive and are not used as an invalidity test.

`actual_pin_map.json` exports the actual LEF-pin metal centers as `expected_net: [[instance, pin, x_um, y_um], ...]`. It is suitable for independent comparison against route edits. The poly directory contains the same pin map because the placed instances and terminal geometry are unchanged.

## DRC evidence

The official pinned `apr/drc_pdk.py` run on the baseline reported three `GC.ANT` markers. Its report was compared with the official poly trial report: the marker XML is byte-for-byte identical (SHA256 `9381da97c0aef5e4a83eb2006f70265ab6b3f223910b35f31cb9f3ecc0c5b935`), so the poly trial introduced no additional official DRC markers. The three baseline markers were matched to the two BUFTH cells (`u_bufth_reset_n`, `u_bufth_clk`) and DFFRB `_542_`; ownership and intended pin nets are described in [postrepair_drc_ownership.md](postrepair_drc_ownership.md). The constant-high D input is omitted from the old route pin map but included in the actual-pin audit.

The constant-tie experiment is documented in [experiments/constant_tie/README.md](../constant_tie/README.md). Its earlier local-spur attempt is retained as a failed checkpoint with a new `V1.CO` marker. The current top-channel candidate passes the rail probe and full-core connectivity comparison: it adds only literal `1'h1` to VDD, keeps VSS separate, and introduces no opens or new short pairs. Its official DRC removes the DFFRB marker and leaves the two baseline BUFTH `GC.ANT` markers. It is still not a DRC-clean core.

The baseline DRC was run with the locked deck and the mandated wrapper:

```sh
python3 scripts/check_toolchain.py
python3 scripts/run_apr.py --design-root experiments/phys_desc5 apr/drc_pdk.py \
  "$PWD/experiments/phys_desc5/build/postrepair_compacted.gds" ishi_vga_core \
  -r "$PWD/experiments/routing_audit/postrepair_baseline.lyrdb" \
  > experiments/routing_audit/postrepair_drc_console.log 2>&1
```

KLayout was 0.30.9. The wrapper's nonzero status for a nonempty DRC report is expected; the logged report count and `.lyrdb` findings are the result. `check_toolchain.py` verifies versions/assets only and does not certify DRC, LVS, STA, or synthesis.

## Reproduction

Run the connectivity check from the repository root:

```sh
python3 scripts/check_toolchain.py
python3 scripts/routing_diagnostics.py \
  --gds experiments/phys_desc5/build/postrepair_compacted.gds \
  --pins experiments/phys_desc5/build/postrepair_pins.json \
  --shapes experiments/phys_desc5/build/postrepair_shapes.json \
  --placement experiments/phys_desc5/layout/placement.json \
  --out experiments/routing_audit

python3 scripts/routing_diagnostics.py \
  --gds experiments/poly_core/build/poly_core_trial.gds \
  --pins experiments/phys_desc5/build/postrepair_pins.json \
  --shapes experiments/poly_core/build/net_shapes.json \
  --placement experiments/phys_desc5/layout/placement.json \
  --out experiments/routing_audit/poly_core --poly
```

Each invocation writes `metal_connectivity.json`, `metal_connectivity.md`, and `actual_pin_map.json` only under its selected audit output directory. The script reads the pinned upstream LEF parser and `rules.py` layer definitions without editing or copying APRtools code.

## Provenance

SHA256 hashes of the inputs and principal outputs used for this report:

| File | SHA256 |
|---|---|
| `experiments/phys_desc5/build/postrepair_compacted.gds` | `7ca31f07ead9b36d20af43e1a732cbf51f22ebd1290e15bbb6346c6d124846ba` |
| `experiments/phys_desc5/build/postrepair_pins.json` | `7527d3299aa41d573e61c5e57e39ce0a99a7084b4e1451e5cabc41f1643ac253` |
| `experiments/phys_desc5/build/postrepair_shapes.json` | `0aa5cbdb489abfdef602492328e4fad7751b784d442050e8577470681db11b07` |
| `experiments/phys_desc5/layout/placement.json` | `fa842099d39d350e9264f1f150d22dabf717923c1dc54bddae28a005ee71e0eb` |
| `tools/APRtools/stdcell/v59_4/TR-1um_cells.lef` | `d765cbf0edd79f9f022df00b1bfc54160fd76631685ce217c02474a2c475ebcc` |
| `tools/APRtools/apr/rules.py` | `d57257f684236eaeed8c1a258a3b6d014fff157a7723d7546fcf86914b81be88` |
| `toolchain.lock.json` | `31f6f929b6be02cb5809d1c0d4d077f7fb7ca0eeb6c0b92d5885eeef2a4ebc5f` |
| `scripts/routing_diagnostics.py` | `6239b2da7e02066cf2b21860611ad6fb01dae1b86b1b61ff8f84ebae7a871540` |
| `experiments/routing_audit/postrepair_baseline.lyrdb` | `9381da97c0aef5e4a83eb2006f70265ab6b3f223910b35f31cb9f3ecc0c5b935` |
| `experiments/routing_audit/postrepair_drc_console.log` | `ef8ed589f005f715ec1b7ee225d2370f2302f88568c6bf9d64ad13058e536d45` |
| `experiments/poly_core/build/poly_core_trial.gds` | `b05c44d0cb1b1e2fda57abbd6d509f2bc2751c1c4a3e2ed666807de8b37c18d1` |
| `experiments/poly_core/build/net_shapes.json` | `d1f0c8c599fed638b0d1e9dcb3ef4fa97d92e691e36c1935fde748e120928b20` |
| `experiments/poly_core/build/poly_core_trial.lyrdb` | `9381da97c0aef5e4a83eb2006f70265ab6b3f223910b35f31cb9f3ecc0c5b935` |
| baseline `metal_connectivity.json` | `e828602d0f20a370619e2df4a63fddbf5bb1dbe2c9394a6921a0e4d488662125` |
| poly `metal_connectivity.json` | `6abe994815a41c2397fa84d0161d13bc314d9b3e6125693e7546414b39e96989` |
