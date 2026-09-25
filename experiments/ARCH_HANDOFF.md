# Architecture experiment handoff (2026-09-25)

Agent `/root/architecture` stops here for requested model handover. No root RTL,
config, dependencies, shared test expectations, or existing experiment files changed.
Owned artifacts: `scripts/arch_*.py`, `experiments/arch_*`.

## Best completed synthesis results

All use the pinned `syn/syn.sh` through `scripts/run_apr.py --design-root`,
existing B rectangle image and same 155 ns constraints, v59_4.

| variant | cells | cell area µm² | notes |
|---|---:|---:|---|
| Baseline B | 375 | 495252 | root pre-existing |
| arch_offset_h80 | **311** | **433987** | best completed H sweep, -12.4% area |
| arch_offset_h40 | 319 | 444572 | registered RGB/sync unchanged |
| arch_offset_h64 | 320 | 448101 | registered RGB/sync unchanged |
| arch_offset_h32 | 321 | 449704 | registered RGB/sync unchanged |
| arch_offset_hm48 | 324 | 451949 | full RTL/gate 2-frequency test PASS |
| arch_offset_hm56 | 327 | 453234 | full RTL/gate 2-frequency test PASS |
| arch_offset_vm64 | 336 | 455478 | best vertical offset so far |
| arch_hoffset16 | 361 | 484026 | full RTL/gate 2-frequency test PASS |
| arch_hoffset56 | 358 | 485308 | full RTL/gate 2-frequency test PASS |
| arch_split_counters | 367 | 498781 | worse, full test PASS |
| arch_sync_counters | 392 | 523158 | worse, full test PASS |
| arch_vevents_binary | 371 | 504234 | worse: 20 Y bands / 7bit countdown |
| arch_vevents_onehot | 370 | 586991 | much worse |
| arch_palette3 | 364 | 487233 | **before** two external BUFTH, flow blocked |

For full sweep results see `arch_base/build/horizontal_sweep.log` and
`vertical_offset_sweep.log`. Each finished experiment contains
`build/synthesis.log`, `out/SYN_RESULTS.txt`, final `out/ishi_vga_core_pnr.v`, STA.

### Meaning of coordinate offset

Only counter numeric representation changes. For H offset +80, reset count is
80, terminal count is (199+80) mod 256 = 23. Every logo bound, active interval,
and HS interval is shifted mod 256. Wrapped intervals use OR comparisons.
Physical placement and pixel coordinates do not move. RGB/sync remain registered.
V offsets are multiples of four; similarly transform 10bit V and 8bit V[9:2].
All external timing, reset phase, and B pixels stay exact in nominal simulation.
`arch_generate.py:offset_core(h_offset,v_offset)` generates combined offsets.
Suggested next step: combine best H=80 with best V=-64, then run full verification
and P&R. Also combine with logic-agent direct/masked logo expressions if useful.

## Existing verification

Upstream syn.sh runs full TB at 6.30 MHz RTL and post-merge gates for every sweep.
Its gate test is before external BUFTH insertion. Stronger independent verifier:

```
python3 scripts/arch_test.py arch_offset_h80 arch_offset_h40
```

This runs RTL and **final PNR netlist** at 6.30 / 6.45 MHz, checks 315017 ticks,
clock-stopped reset, two-edge reset-release, entire frame dump exact against
root tests/expected_frame.hex; saves build/verification.json+log per experiment.
Already verified: hoffset16, hoffset56, split_counters, sync_counters,
offset_hm48, offset_hm56. **h80 and newer sweep results still need this final test.**
No architecture variant has been placed/routed by this agent yet.

## Processes deliberately left running

At handover the following independent runs were active (no new work started after
parent requested handover):

- Vertical offsets: exec session **8079**, shell PID 253990, sweep PID **253991**.
  Command `python3 scripts/arch_sweep.py arch_offset_vm128 arch_offset_vm96
  arch_offset_vm76 arch_offset_vm64 arch_offset_vm32 arch_offset_v32
  arch_offset_v64 arch_offset_v128 arch_offset_v256 arch_offset_v500`.
  Log `experiments/arch_base/build/vertical_offset_sweep.log`.
  Last active: v128; v256,v500 still pending at check.
- RGB factor: exec session **56141**, shell PID 258743, sweep PID **258746**.
  Command `python3 scripts/arch_sweep.py arch_rgb5 arch_rgb3`.
  Log `experiments/arch_base/build/rgb_factor_sweep.log`.
  Last active: rgb5.

Horizontal sweep session 75666, vertical-event session 83479, verification
sessions 29728 and 38721 completed. Palette initial session 82020 failed.
The sweep script writes `arch_base/build/sweep_latest.json` on finish, shared
by sweeps, so that convenience file may be overwritten; individual logs and
per-variant synthesis files are authoritative.

## RGB factor experiments

`arch_rgb5` retains five RGB output FFs, computes B0=R0|R1.
`arch_rgb3` retains R1,G1,G0 FFs; all seven colors (six logo + black) uniquely
identify themselves with these three bits. Other bits use shallow logic:
R0=G0|(~R1&G1); B1=G1|(~R1&G0); B0=R1|G1|G0.
This avoids arbitrary palette decode overhead. Unlike coordinate offsets,
**three outputs become combinational after FFs**; output delay and transition
glitches need explicit review despite sampled pixel equivalence. Not a drop-in
promise of unchanged edge waveforms. It may improve cells, pending results.

Arbitrary `arch_palette3` had internally mapped BUFTH from ABC. The unmodified
upstream insert_bufth.py refuses if it sees any BUFTH anywhere, even an internal
non-input buffer, and stopped at stage6. Preserve its raw net and code. Parent
is considering ABC -dont_use BUFTH in a separate synthesis frontend. Do not
edit upstream or silently exclude the two external input buffers from counts.

## Generator/reproduction caveats

- `arch_generate.py` writes all initial/counter/offset variants; do not rerun it
  while another process is reading those sources/configs.
- Config files are **copies of design settings, not upstream scripts**. They
  import config_base freshly and assign values before finalize(globals()), so
  derived paths stay isolated, avoiding runpy finalized-dict contamination.
- Each experiment tests/expected_frame.hex is a symlink to root immutable
  approved reference; generation does not mutate the reference.
- `arch_sweep.py` runs only one upstream build at a time; multiple sweeps may
  run together, but machine has 5 CPUs and rest of team also active.
- No claims of official DRC/LVS, routed fit, or parasitic timing.
