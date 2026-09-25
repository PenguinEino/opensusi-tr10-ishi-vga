#!/usr/bin/env python3
"""Fresh RTL/gate frame tests on the adopted design plus binary startup model."""
import hashlib
import json
from pathlib import Path
import subprocess
from check_toolchain import ROOT, verify


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    verify();d=ROOT/'designs/grid_power';b=d/'build';b.mkdir(exist_ok=True)
    source=ROOT/'experiments/a_metal_g_power'
    fixed=['ishi_logo.v','ishi_vga_core.v','out/ishi_vga_core_pnr.v','tests/expected_frame.hex',
           'tests/tb_rtl.v','tests/tb_gates.v','build/tr1um_cells.v']
    assert all(sha(d/f)==sha(source/f) for f in fixed)
    logs={}
    for kind,files in [('rtl',['ishi_vga_core.v','ishi_logo.v']),
                       ('gates',['out/ishi_vga_core_pnr.v','build/tr1um_cells.v'])]:
        exe=b/(kind+'.vvp')
        subprocess.run([str(ROOT/'.tools/bin/iverilog'),'-g2012','-s','tb_vga','-o',str(exe),
                        str(d/f'tests/tb_{kind}.v'),*[str(d/f) for f in files]],cwd=d,check=True)
        p=subprocess.run([str(ROOT/'.tools/bin/vvp'),str(exe)],cwd=d,check=True,capture_output=True,text=True)
        assert 'PASS:' in p.stdout and 'FAIL' not in p.stdout
        (b/(kind+'.log')).write_text(p.stdout+p.stderr);logs[kind]=p.stdout.strip()
    # Exact two-state transition model of the two counters. Traverse every
    # h[6:0],v[9:0] pair; this is not analog power-up or RTL formal proof.
    count=128*1024;distance=[-1]*count;cycles=[]
    def step(s):
        h=s&127;v=s>>7
        return ((500 if v==0 else (v+1)&1023)<<7)|71 if h==100 else (v<<7)|((h-1)&127)
    for start in range(count):
        if distance[start]>=0:continue
        path=[];seen={};s=start
        while distance[s]<0 and s not in seen:
            seen[s]=len(path);path.append(s);s=step(s)
        if s in seen:
            i=seen[s];cycles.append(len(path)-i)
            for state in path[i:]:distance[state]=0
            path=path[:i]
        for state in reversed(path):distance[state]=distance[step(state)]+1
    assert cycles==[52500] and max(distance)<=50029
    result={'status':'PASS','adopted_artwork_and_netlist_byte_identical':True,'frame_tests':logs,
            'startup_model':{'binary_counter_states':count,'cycles_ticks':cycles,
                             'max_ticks_into_cycle':max(distance),'clock_hz':3150000},
            'limitations':'Frame tests initialize FFs in fixture only; unit-delay gates; startup graph is a two-state model, not analog or RTL formal proof.',
            'hashes':{str((d/f).relative_to(ROOT)):sha(d/f) for f in fixed}}
    result['hashes'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
    (b/'functional_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
