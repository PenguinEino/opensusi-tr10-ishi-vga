#!/usr/bin/env python3
"""Replay clock ECO from the frozen pre-review core, then fresh DRC/LVS/STA."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from check_toolchain import ROOT, verify
from replay_power_core import sha
from validate_route_candidate import report_markers
import klayout.db as db


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
    verify();d=(ROOT/a.out).resolve();assert d.is_relative_to(ROOT) and not d.exists()
    (d/'build').mkdir(parents=True)
    origin=ROOT/'experiments/a_clock_tree'
    for name in ['config.py','clock_report.tcl','clock_electrical.tcl']:
        shutil.copyfile(origin/name,d/name)
    env=dict(os.environ,PYTHONHASHSEED='0')
    def call(log,args,allowed=(0,)):
        with (d/'build'/log).open('w') as f:
            p=subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        assert p.returncode in allowed,(log,p.returncode)
    def apr(log,*args,allowed=(0,)):
        call(log,[ROOT/'scripts/run_apr.py','--design-root',d,*args],allowed)
    call('eco.log',[ROOT/'scripts/clock_tree_eco.py','--design-root',d])
    assert sha(d/'build/candidate.gds')=='299b3203897dd4dffca7fb1a260a68dbd577c4ac4f98fb105cfe9e8579cf650c'
    apr('reference.log','apr/mklvsnet.py','--netlist','out/ishi_vga_core_pnr.v','--placement','layout/placement.json','--out','build/ishi_vga_core.spice')
    apr('drc.log','apr/drc_pdk.py','build/candidate.gds','ishi_vga_core','-r','build/drawing.lyrdb','--mdp',allowed=(0,1))
    assert not report_markers(d/'build/drawing.lyrdb')
    assert report_markers(d/'build/candidate_mdp.lyrdb')==report_markers(ROOT/'release/ishi_vga_grid_power_core/experiments/a_power_escape/build/candidate_mdp.lyrdb')
    apr('lvs.log','apr/lvs_pdk.py','build/candidate.gds','ishi_vga_core','--sch','build/ishi_vga_core.spice','-r','build/core.lvsdb')
    lvs=db.LayoutVsSchematic();lvs.read(str(d/'build/core.lvsdb'));x=lvs.xref()
    assert all(p.status()==x.Match and p.first() and p.second() for p in x.each_circuit_pair())
    apr('sta.log','syn/sta/sta.sh','out/ishi_vga_core_pnr.v','ishi_vga_core','317.460317','clock_report.tcl')
    assert json.loads((d/'out/STA_ishi_vga_core.guard.json').read_text())['status']=='PASS'
    result={'status':'PASS','scope':'byte-identical clock ECO, fresh drawing/MDP/strict LVS/guarded cell STA; no frame or wire RC',
            'gds_sha256':sha(d/'build/candidate.gds'),'drawing_drc':0,'mask_warnings':1,
            'hashes':{str(p.relative_to(ROOT)):sha(p) for p in [d/'config.py',d/'build/candidate.gds',d/'build/drawing.lyrdb',d/'build/core.lvsdb',d/'out/STA_ishi_vga_core.guard.json',Path(__file__)]}}
    (d/'replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
