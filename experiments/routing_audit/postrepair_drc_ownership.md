# Official PDK DRC baseline ownership audit

The locked `tools/TR-1um` deck, run through `scripts/run_apr.py --design-root experiments/phys_desc5 apr/drc_pdk.py`, reported three `GC.ANT` markers in `postrepair_compacted.gds`. KLayout 0.30.9 was used. The entry point returns failure when the XML report contains items (the summary counted 3). The markers are not caused by the new GC/CO core-poly trial: the trial's separate report contains the same three GC.ANT markers and no additions.

The report polygons were intersected with hierarchical GDS shapes, then matched to placed instance transforms and placement signal metadata:

| Marker area (µm) | Instance | Cell | Placed signal pins / intended nets |
|---|---|---|---|
| x 1005.4–1014.3, y 1626.1–1654.0 | `u_bufth_reset_n` | BUFTH | A=`reset_n`, Y=`reset_n_buf` |
| x 1588.6–1597.5, y 1626.1–1654.0 | `u_bufth_clk` | BUFTH | A=`clk`, Y=`clk_buf` |
| x 1627.2–1631.1, y 1626.1–1654.1 | `_542_` | DFFRB | D=`1'h1`, Q=`reset_pipe[0]`, CK=`clk_buf`, RSTB=`reset_n_buf` |

These are GC shapes owned by two BUFTH cells and one DFFRB cell. The third marker overlaps the un-routed constant-high D input pin on `_542_`; the trial to tie this pin to the row VDD rail must be checked separately. The first two occur inside the input Schmitt-buffer cells and are retained in the baseline. They remain reported violations; this audit does not waive them.

Reproduce and retain the full report with:

```sh
mkdir -p experiments/routing_audit
python3 scripts/check_toolchain.py
python3 scripts/run_apr.py --design-root experiments/phys_desc5 \
  apr/drc_pdk.py "$PWD/experiments/phys_desc5/build/postrepair_compacted.gds" \
  ishi_vga_core -r "$PWD/experiments/routing_audit/postrepair_baseline.lyrdb" \
  > experiments/routing_audit/postrepair_drc_console.log 2>&1
```
