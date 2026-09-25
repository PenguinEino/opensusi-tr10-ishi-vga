# ISHI VGA implementation rules

- Use the pinned submodules `tools/APRtools` and `tools/TR-1um`. Read `docs/APRTOOLS_ADOPTION.md` and `toolchain.lock.json` before implementation.
- Only the PCell technology lookup patch recorded in the lock is applied to APRtools. Run `scripts/apply_toolchain_patches.py` after a fresh checkout; do not remove it or allow arbitrary upstream edits. See `docs/IMPLEMENTATION.md` for the executed reproducer and remaining physical-design work.
- APRtools scripts are upstream dependencies, not templates to copy into this design. Do not execute scripts from `legacy/`, old I2C/SPI/TD4 design repositories, or `research/digital_flow/` (research snapshots only).
- Use v59_4 GDS/LEF/SPICE and its characterized Liberty together. Do not use v64_8, PDK's identically named standard-cell GDS, or the obsolete `TR-1um_PNR.*` derivative.
- Run `python3 scripts/check_toolchain.py` before a build, and use `scripts/run_apr.py` for upstream entry points. No automatic dependency updates or fallback to another local PDK.
- Where upstream Markdown disagrees, check the current decisions/ledger and pinned executable code. Record the discrepancy; do not silently choose an older path.
- The pinned corrected GIO frame and its matching frozen SPICE references are a set. Final integration must also satisfy the organizer's actual template and pin assignment.
- Keep reproducible design settings in the design `config.py`; no inherited APR_* tuning variables. Do not copy process constants out of upstream rules.py.
- Existing image previews are design references, not RTL simulation results. DRC/LVS/STA checks must be reported separately from version checks.
- Current clock architecture (user update 2026-09-25): external CLK only; do not integrate a ring oscillator. No ring-output pad, external clock jumper, or internal clock mux is required. Historical trial configs retain an unused pad12 reservation; it is not a ring instance.
- Latest target: half area and seven pins. Use the conservative working budget 1800 x 900 um and seven terminals including VDD but excluding common VSS. The user adopted `g_power` (grid + five power branches). Current logical design: `designs/grid_power`; current physical signoff and handoff: `docs/POWER_GRID_IMPLEMENTATION.md`. Preserve prior exact A/B and comparison artifacts. Frame integration remains paused.
