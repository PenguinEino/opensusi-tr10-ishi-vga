#!/usr/bin/env python3
"""Design-level Yosys mapping experiment; upstream postprocessing stays pinned.

This is intentionally a separate experimental front end, not syn/syn.sh.
All downstream transforms and STA are upstream entry points run via run_apr.py.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
from check_toolchain import ROOT, verify

MODES={
    'noabc': ('-noabc', ''),
    'delay155': ('-noabc', '-D 155000'),
    'fast': ('-noabc', '-fast'),
    'area': ('-noabc', '-script +strash;ifraig;scorr;dc2;map,-a;buffer;dnsize;stime,-p'),
}

def run(args, cwd=ROOT, log=None):
    env=dict(os.environ)
    env['PATH']=str(ROOT/'.tools/bin')+os.pathsep+env['PATH']
    r=subprocess.run([str(x) for x in args],cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
    if log: Path(log).write_text(r.stdout)
    return r.stdout

def main(mode):
    lock=verify()
    base=ROOT/'experiments'/('map_'+mode)
    (base/'build').mkdir(parents=True,exist_ok=True);(base/'out').mkdir(exist_ok=True)
    if not (base/'tests').exists(): (base/'tests').symlink_to('../../tests',target_is_directory=True)
    config='''from pathlib import Path
import runpy
PROJECT=Path(__file__).resolve().parents[2]
settings=runpy.run_path(str(PROJECT/'config.py'))
globals().update({k:v for k,v in settings.items() if not k.startswith('__')})
SYN_RTL=[str(PROJECT/'rtl/ishi_vga_core.v'),str(PROJECT/'rtl/ishi_logo.v')]
MAPPING_EXPERIMENT=%r
'''
    (base/'config.py').write_text(config % mode)
    lib=ROOT/lock['assets']['liberty']['path']
    shutil.copyfile(ROOT/'out/abc.constr',base/'out/abc.constr')
    shutil.copyfile(ROOT/'build/tr1um_cells.v',base/'build/tr1um_cells.v')
    synopt,abcopt=MODES[mode]
    script=f'''read_verilog {ROOT/'rtl/ishi_vga_core.v'} {ROOT/'rtl/ishi_logo.v'}
hierarchy -check -top ishi_vga_core
synth -top ishi_vga_core -flatten {synopt}
dfflibmap -liberty {lib}
abc -liberty {lib} -constr out/abc.constr {abcopt}
opt_clean
write_verilog -noattr out/ishi_vga_core.v
stat -liberty {lib}
'''
    (base/'mapping.ys').write_text(script)
    run([ROOT/'.tools/bin/yosys','-s','mapping.ys'],base,base/'build/mapping.log')
    def apr(entry,*args):
        return run([sys.executable,ROOT/'scripts/run_apr.py','--design-root',base,entry,*args])
    logs=[]
    logs.append(apr('apr/dedup_gates.py','out/ishi_vga_core.v','out/ishi_vga_core_dedup.v'))
    logs.append(apr('apr/merge_muxdffrb_rslatch.py','--in','out/ishi_vga_core_dedup.v','--out','out/ishi_vga_core_merged.v'))
    logs.append(apr('apr/insert_bufth.py','out/ishi_vga_core_merged.v','out/ishi_vga_core_pnr.v','--nets','clk,reset_n'))
    logs.append(apr('apr/syn_report.py','ishi_vga_core','-n','out/ishi_vga_core_pnr.v','--brief'))
    logs.append(apr('syn/sta/sta.sh','out/ishi_vga_core_pnr.v','ishi_vga_core','155'))
    (base/'build/synthesis.log').write_text('\n'.join(logs))
    # Entire externally visible output waveform, including reset and wrap.
    run([ROOT/'.tools/bin/iverilog','-g2012','-s','tb_vga','-o','build/gates.vvp',ROOT/'tests/tb_vga.v','out/ishi_vga_core_pnr.v','build/tr1um_cells.v'],base)
    tests=[]
    for mhz,half in [(6.3,'79.365079365'),(6.45,'77.519379845')]:
        dump=f'build/frame_{mhz}.hex'
        output=run([ROOT/'.tools/bin/vvp','build/gates.vvp','+HALF_NS='+half,'+DUMP='+dump],base)
        assert 'PASS: 315017 pixel ticks' in output and 'FAIL' not in output
        assert (base/dump).read_bytes()==(ROOT/'tests/expected_frame.hex').read_bytes()
        tests.append(output)
    (base/'build/tests.log').write_text('\n'.join(tests))
    inputs=[ROOT/'rtl/ishi_vga_core.v',ROOT/'rtl/ishi_logo.v',base/'config.py',base/'mapping.ys',base/'out/abc.constr',base/'out/ishi_vga_core_pnr.v']
    (base/'result.json').write_text(json.dumps({'mode':mode,'test':'PASS 2 clocks × 315017 ticks','sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}},indent=2)+'\n')
    print(mode+'\n'+logs[-2]+logs[-1])

if __name__=='__main__':
    for mode in sys.argv[1:] or MODES:main(mode)
