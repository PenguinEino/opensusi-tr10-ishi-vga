# H/V counter offset combinations and exact B-image logic

All synthesis runs used the pinned `syn/syn.sh` through `scripts/run_apr.py --design-root`; `scripts/check_toolchain.py` passed before each build. Candidate sources/configs and logs are isolated under `experiments/combine_*`. The root RTL, root config, and approved frame reference were not modified.

## Best result

`combine_direct_bounds_h80_v500` is the best completed candidate: **285 cells, 409,289 µm²**, versus `arch_offset_h80` at 311 cells / 433,987 µm² (5.7% lower area). It uses H counter offset +80 and V offset +500, which is +125 in the 8-bit logo Y coordinate. The logo logic uses direct RGB bit equations and split ordinary range comparisons for intervals that wrap at 256. This candidate passed all 65,536 logo-coordinate comparisons and full 315,017-tick frames against `tests/expected_frame.hex` for RTL and the final synthesis PNR netlist at both 6.30 and 6.45 MHz.

| Candidate (H=80, V=500) | Cells | Area (µm²) | Min reg-reg period | Coordinate / frame checks |
|---|---:|---:|---:|---|
| direct bounds | **285** | **409,289** | 45.652 ns | PASS |
| BDD, Y then X MSB | 316 | 454,196 | 50.216 ns | PASS |
| direct dyadic masks | 344 | 484,668 | 40.509 ns | PASS |
| interval POS | 346 | 489,158 | 42.388 ns | PASS |

Each completed candidate passed RTL and final PNR-netlist frame checks at both frequencies, with asynchronous stopped-clock reset and reset release included. STA is pre-route; no parasitics, physical fit, DRC, or LVS result is claimed. Detailed hashes and verification records are in each candidate's `build/metrics.json`, `build/verification.log`, and `out/STA_ishi_vga_core.txt`.

## Blocked candidate

`combine_direct_bounds_h80_v-64` passed the 65,536-coordinate check and upstream RTL plus merged-gate testbench (315,017 ticks). Synthesis reported 307 cells / 425,969 µm² before final PNR. The merged netlist had 304 instances, including internal `BUFTH` on `v[5]` and `h[4]`; upstream `insert_bufth.py` stopped because it treats any existing `BUFTH` as a duplicate-input-buffer condition. This is a partial synthesis result, not a final cell/area result; no final PNR-netlist two-frequency verification or STA result is available. The upstream dependency was left untouched.

## Architecture references and reproduction

`python3 scripts/arch_test.py arch_offset_h80` passed the 6.30/6.45 MHz RTL and final-netlist checks (four combinations). The vertical-offset sweep with H=0 completed with: V=-64, 336 cells / 455,478 µm²; V=500, 335 / 452,592; V=128, 335 / 463,177; V=-76, 340 / 463,497; V=-96, 349 / 476,328; V=-128, 361 / 479,536; V=-32, 347 / 470,554; V=32, 351 / 474,404; V=64, 367 / 490,120; V=256, 371 / 492,687. H=80/V=500 is the best fully verified result from this combination batch.

Regenerate the four H=80/V=500 forms and rerun the serial validation/builds with:

```sh
python3 scripts/combine_generate.py 80 500
python3 scripts/combine_test.py \
  combine_direct_bounds_h80_v500 \
  combine_direct_masked_h80_v500 \
  combine_axis_pos_h80_v500 \
  combine_bdd_yx_msb_h80_v500
```

The generator splits wrapped intervals explicitly; comparisons with an exclusive upper edge of 256 omit that upper comparison to avoid truncating `8'd256` to zero. The BDD truth table maps candidate `(h,y)` to reference `((h-80) mod 256, (y-125) mod 256)`.
