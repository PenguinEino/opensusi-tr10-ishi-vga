#!/usr/bin/env python3
"""Probe pinned config_base resolution without creating a design config or layout."""
import json
import os
import sys
from pathlib import Path
from check_toolchain import ROOT, verify

lock = verify()
os.environ['TR1UM_PDK'] = str(ROOT / 'tools/TR-1um')
sys.path.insert(0, str(ROOT / 'tools/APRtools/apr'))
import config_base as base

# Synthetic namespace for resolving library paths ONLY. Not a VGA floorplan.
ns = {k: v for k, v in vars(base).items() if not k.startswith('_')}
ns.update(ROOT=str(ROOT), TOP_CELL_NAME='audit_only', CHIP_TOP_CELL='tr_1um_audit_only',
          STDCELL='v59_4')
base.finalize(ns)
expected = {'LIB_GDS':'cell_gds', 'CELL_GDS':'cell_gds',
            'LIB_LEF':'cell_lef', 'LEF_PATH':'cell_lef',
            'LIBERTY':'liberty', 'SYN_LIB':'liberty', 'CELL_INFO':'cell_info',
            'FRAME_GDS':'frame_gds', 'RING_OSC_GDS':'ring_gds', 'RING_OSC_LEF':'ring_lef'}
resolved = {}
for key, asset in expected.items():
    actual = Path(ns[key]).resolve()
    wanted = (ROOT / lock['assets'][asset]['path']).resolve()
    if actual != wanted:
        raise SystemExit(f'{key}: unexpected resolution {actual}; wanted {wanted}')
    resolved[key] = str(actual.relative_to(ROOT))
resolved['FRAME_LVS_SPICE_default'] = ns.get('FRAME_LVS_SPICE')
resolved['FRAME_LVS_SPICE_required'] = lock['assets']['frame_lvs']['path']
print(json.dumps({'scope':'upstream path-resolution probe, NOT a design configuration',
                  'aprtools_commit':lock['repositories']['aprtools']['commit'],
                  'resolved':resolved}, indent=2))
