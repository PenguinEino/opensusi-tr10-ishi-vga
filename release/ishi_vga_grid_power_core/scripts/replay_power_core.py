#!/usr/bin/env python3
"""Replay selected repair/labels/escapes from frozen APR checkpoint, then signoff.

Writes only a new build directory; never overwrites a measured experiment.
The pre-repair route is an archived input, not a fresh placement claim.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from check_toolchain import ROOT, verify


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='build/power_core_replay')
    a=ap.parse_args();verify();dst=(ROOT/a.out).resolve()
    assert dst.is_relative_to(ROOT) and not dst.exists(), 'Choose a new workspace output directory'
    dst.mkdir(parents=True)
    env=dict(os.environ,PYTHONHASHSEED='0')
    records=[]; mapping={}
    stages=[('a_power_fix066','MAZE_ROUTE','maze_route.py','candidate.gds'),
            ('a_power_fix172eq','MAZE_ROUTE','power_maze_route.py','candidate.gds'),
            ('a_power_labels','CORE_PORT_LABELS','label_power_ports.py','labeled_core.gds'),
            ('a_power_escape','CORE_ESCAPE','route_core_escape.py','candidate.gds')]
    for name,key,script,output in stages:
        old=ROOT/'experiments'/name;new=dst/name;(new/'build').mkdir(parents=True)
        cfg=(old/'config.py').read_text()
        st=next(ast.literal_eval(n.value) for n in ast.parse(cfg).body if isinstance(n,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id==key for t in n.targets))
        oldsource=st['source_gds'];st['source_gds']=mapping.get(oldsource,oldsource)
        assert sha(ROOT/st['source_gds'])==st['source_sha256']
        cfg,n=re.subn(r'^'+key+r' = .*$',lambda m:key+' = '+repr(st),cfg,flags=re.M);assert n==1
        (new/'config.py').write_text(cfg)
        with (new/'build/replay.log').open('w') as log:
            subprocess.run([sys.executable,str(ROOT/'scripts'/script),'--design-root',str(new)],
                           cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        actual=new/'build'/output;expected=old/'build'/output
        assert sha(actual)==sha(expected),(name,'byte-for-byte GDS replay differs')
        mapping[str(expected.relative_to(ROOT))]=str(actual.relative_to(ROOT))
        records.append({'stage':name,'gds_sha256':sha(actual),'identical':True})
        print(name,'GDS SHA256 MATCH',flush=True)
    final=dst/'a_power_escape';b=final/'build'
    ref=ROOT/'experiments/a_power_flex4/build/ishi_vga_core.spice'
    commands=[('drc.log',[sys.executable,str(ROOT/'scripts/run_apr.py'),'--design-root',str(final),
              'apr/drc_pdk.py','build/candidate.gds','ishi_vga_core','-r','build/drawing.lyrdb','--mdp']),
              ('lvs.log',[sys.executable,str(ROOT/'scripts/run_apr.py'),'--design-root',str(final),
              'apr/lvs_pdk.py','build/candidate.gds','ishi_vga_core','--sch',str(ref),'-r','build/core.lvsdb']),
              ('audit.log',[sys.executable,str(ROOT/'scripts/routing_diagnostics.py'),
              '--gds',str(b/'candidate.gds'),'--pins',str(ROOT/'experiments/a_power_flex4/build/audit/actual_pin_map.json'),
              '--shapes',str(ROOT/'experiments/a_power_flex4/build/diagnostic_shapes.json'),
              '--placement',str(ROOT/'experiments/a_power_flex4/layout/placement.json'),'--out',str(b/'audit'),'--poly'])]
    for logname,cmd in commands:
        with (b/logname).open('w') as log:
            p=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        assert p.returncode in ((0,1) if logname=='drc.log' else (0,)),(logname,p.returncode)
    subprocess.run([sys.executable,str(ROOT/'scripts/verify_power_core.py'),'--design-root',str(final),
                    '--reference',str(ref)],cwd=ROOT,env=env,check=True)
    report={'status':'PASS','scope':'frozen APR checkpoint through local repair, labels, escapes, fresh DRC/LVS',
            'stages':records,'verification':str((b/'verification.json').relative_to(ROOT)),
            'final_gds_sha256':sha(b/'candidate.gds'),'script_sha256':sha(Path(__file__))}
    (dst/'replay.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
