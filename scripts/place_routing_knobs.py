#!/usr/bin/env python3
"""Route the frozen root B placement under explicit config-only routing knobs."""
import argparse, json, shutil
from place_sweep import ROOT, make, run
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--prl',type=int,default=5);p.add_argument('--span-pack',action='store_true');p.add_argument('--source',default='');a=p.parse_args()
d=make(a.name,7,296,1,80)
source=ROOT/a.source if a.source else ROOT
if a.source:
    (d/'config.py').write_text((source/'config.py').read_text())
    shutil.copyfile(source/'out/ishi_vga_core_pnr.v',d/'out/ishi_vga_core_pnr.v')
    shutil.copyfile(source/'source_manifest.json',d/'source_manifest.json')
shutil.copytree(source/'layout/step4',d/'layout/step4',dirs_exist_ok=True)
knobs={'PRL_MIN_PINS':a.prl,'SPAN_LANE_PACK':a.span_pack}
with (d/'config.py').open('a') as f:
    f.write('''\n# Pinned APRtools reads these routing controls through cfg.getenv, not globals.\n# Design-owned adapter makes them reproducible without inherited APR_* values.\n''')
    f.write('ROUTING_KNOBS = '+repr(knobs)+'\n')
    f.write('''_upstream_getenv = getenv\ndef getenv(name, default=None, cast=None):\n    if name not in ROUTING_KNOBS:\n        return _upstream_getenv(name, default, cast)\n    value = ROUTING_KNOBS[name]\n    return cast(value) if cast else value\n''')
(d/'routing_knobs.json').write_text(json.dumps({'source_placement':str(source.relative_to(ROOT)),'knobs':knobs},indent=2)+'\n')
if run(d,'apr/route.py',['--to','6'],log='route_step6.log'):raise SystemExit(2)
run(d,'apr/squeeze_channels.py',['--in-gds','layout/step6/route_step_2_routed_raw.gds','-o','build/diagnostic_compacted.gds','--pin-map-in','layout/pin_map.json','--pin-map-out','build/diagnostic_pins.json','--net-shapes-in','layout/net_shapes.json','--net-shapes-out','build/diagnostic_shapes.json'],log='diagnostic_compaction.log')
print(d)
