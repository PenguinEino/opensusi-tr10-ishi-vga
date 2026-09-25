#!/usr/bin/env python3
"""Replay the letter animation from frozen static geometry, with fresh signoff checks."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
import klayout.db as db
from letter_animation_eco import ROOT,sha,verify
from validate_route_candidate import report_markers

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--verify-existing',action='store_true');ap.add_argument('--expected-gds',type=Path,default=ROOT/'release/ishi_vga_letter_scan_core/ishi_vga.gds');a=ap.parse_args();verify()
    d=a.out.resolve();assert d.is_relative_to(ROOT)
    if not a.verify_existing:
        assert not d.exists();(d/'build').mkdir(parents=True)
    source=ROOT/'experiments/a_letter_scan_eco';env=dict(os.environ,PYTHONHASHSEED='0')
    for name in ['config.py','ishi_vga_core.v','ishi_logo.v','clock_electrical.tcl','clock_report.tcl']:
        if a.verify_existing:assert sha(source/name)==sha(d/name)
        else:shutil.copyfile(source/name,d/name)
    if not a.verify_existing:
        (d/'patch_split_toggle/build').mkdir(parents=True)
        for name in ['config.py','letter_scan_patch.v']:shutil.copyfile(source/'patch_split_toggle'/name,d/'patch_split_toggle'/name)
    def call(log,args,allowed=(0,)):
        with (d/'build'/log).open('w') as f:proc=subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        assert proc.returncode in allowed,(log,proc.returncode)
        print(log,'done',flush=True)
    def apr(log,*args,allowed=(0,)):
        call(log,[ROOT/'scripts/run_apr.py','--design-root',d,*args],allowed)
    if not a.verify_existing:
        call('patch_synthesis.log',[ROOT/'scripts/run_apr.py','--design-root',d/'patch_split_toggle','syn/syn.sh'])
        for name in ['out','layout']:(d/name).mkdir()
        call('placement.log',[ROOT/'scripts/letter_animation_eco.py','--design-root',d])
        call('routing.log',[ROOT/'scripts/route_letter_animation_eco.py','--design-root',d])
        call('repair.log',[ROOT/'scripts/repair_letter_animation_drc.py','--design-root',d])
    assert sha(d/'build/candidate.gds')==sha(a.expected_gds)
    apr('reference.log','apr/mklvsnet.py','--netlist','out/ishi_vga_core_pnr.v','--placement','layout/placement.json','--out','build/ishi_vga_core.spice')
    apr('drc.log','apr/drc_pdk.py','build/candidate.gds','ishi_vga_core','-r','build/drawing.lyrdb','--mdp',allowed=(0,1))
    assert not report_markers(d/'build/drawing.lyrdb')
    assert report_markers(d/'build/candidate_mdp.lyrdb')==report_markers(ROOT/'release/ishi_vga_letter_scan_core/reproduce/static_mdp.lyrdb')
    apr('lvs.log','apr/lvs_pdk.py','build/candidate.gds','ishi_vga_core','--sch','build/ishi_vga_core.spice','-r','build/core.lvsdb')
    lvs=db.LayoutVsSchematic();lvs.read(str(d/'build/core.lvsdb'));x=lvs.xref()
    assert all(p.status()==x.Match and p.first() and p.second() for p in x.each_circuit_pair())
    apr('sta.log','syn/sta/sta.sh','out/ishi_vga_core_pnr.v','ishi_vga_core','317.460317','clock_report.tcl')
    assert json.loads((d/'out/STA_ishi_vga_core.guard.json').read_text())['status']=='PASS'
    apr('extraction.log','apr/klayout_extract.py','build/candidate.gds','ishi_vga_core','--no-combine','-o','build/core.extracted')
    call('audit.log',[ROOT/'scripts/routing_diagnostics.py','--gds',d/'build/candidate.gds','--pins',d/'build/pins.json','--shapes',d/'build/shapes.json','--placement',d/'layout/placement.json','--out',d/'build/audit'])
    call('functional.log',[ROOT/'scripts/test_letter_animation_eco.py','--design-root',d])
    assert json.loads((d/'build/functional/verification.json').read_text())['status']=='PASS'
    result={'status':'PASS','scope':'byte-identical GDS, fresh DRC/LVS/STA, 128 continuous RTL/gate frames',
            'gds_sha256':sha(d/'build/candidate.gds'),'size_um':[1792.8,897.2],
            'hashes':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),d/'config.py',d/'build/candidate.gds',d/'build/drawing.lyrdb',d/'build/core.lvsdb',d/'out/STA_ishi_vga_core.guard.json',d/'build/functional/verification.json']}}
    (d/'replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
