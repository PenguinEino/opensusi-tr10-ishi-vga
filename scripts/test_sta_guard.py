#!/usr/bin/env python3
"""End-to-end STA positive/negative controls through the actual wrapper."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from check_toolchain import ROOT, verify


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
    verify();dest=(ROOT/a.out).resolve();assert dest.is_relative_to(ROOT) and not dest.exists()
    dest.mkdir(parents=True);results={}
    cases={'corrected_core':(False,'set_propagated_clock [all_clocks]\n',0),
           'original_cap_violation':(True,'set_propagated_clock [all_clocks]\n',1),
           'tcl_error':(False,'error {INTENTIONAL_REVIEW_NEGATIVE_CONTROL}\n',1),
           'incomplete_report':(False,'exit\n',1)}
    for name,(old,tcl,expected) in cases.items():
        d=dest/name;(d/'out').mkdir(parents=True)
        for f in ['config.py','clock_electrical.tcl']:shutil.copyfile(ROOT/'experiments/a_clock_tree'/f,d/f)
        net=ROOT/('release/ishi_vga_grid_power_core/designs/grid_power/out/ishi_vga_core_pnr.v' if old else 'designs/grid_power/out/ishi_vga_core_pnr.v')
        shutil.copyfile(net,d/'out/ishi_vga_core_pnr.v');(d/'control.tcl').write_text(tcl)
        with (d/'sta.log').open('w') as log:
            p=subprocess.run([sys.executable,str(ROOT/'scripts/run_apr.py'),'--design-root',str(d),'syn/sta/sta.sh','out/ishi_vga_core_pnr.v','ishi_vga_core','317.460317','control.tcl'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        report=json.loads((d/'out/STA_ishi_vga_core.guard.json').read_text())
        assert p.returncode==expected and report['status']==('PASS' if not expected else 'FAIL'),name
        results[name]={'exit':p.returncode,'guard':report};print(name,'expected exit',p.returncode,flush=True)
    (dest/'results.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':main()
