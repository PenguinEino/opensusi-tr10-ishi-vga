#!/usr/bin/env python3
"""Standalone checks of the animated submission; write new runs outside the bundle."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from check_letter_wave import check
from verify_bundle import verify

ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('mode',choices=['saved-spice','spice','rtl-gates'])
    ap.add_argument('--out',type=Path)
    ap.add_argument('--case',help='One named transistor case; default: all cases')
    a=ap.parse_args();verify()
    names=json.loads((ROOT/'simulation/cases.json').read_text())
    if a.case:
        assert a.case in names;names=[a.case]
    if a.mode=='saved-spice':
        results={name:check(ROOT/'simulation'/name/'wave.raw.gz',json.loads((ROOT/'simulation'/name/'case.json').read_text()),ROOT/'tests/expected_states.hex') for name in names}
    else:
        assert a.out is not None, '--out required for new results'
        out=a.out.resolve();assert not out.is_relative_to(ROOT) and not out.exists()
        out.mkdir(parents=True)
        if a.mode=='spice':
            shutil.copytree(ROOT/'simulation',out/'simulation');results={}
            for name in names:
                case=out/'simulation'/name
                with (case/'rerun.log').open('w') as log:
                    subprocess.run(['ngspice','-n','-b','-r','rerun.raw','tb.spice'],cwd=case,stdout=log,stderr=subprocess.STDOUT,check=True)
                results[name]=check(case/'rerun.raw',json.loads((case/'case.json').read_text()),ROOT/'tests/expected_states.hex')
        else:
            tb=(ROOT/'verification/functional/tb.v').read_text()
            import re
            tb,n=re.subn(r'\$readmemh\("[^"]+",reference\);',lambda m:'$readmemh("'+str(ROOT/'tests/expected_frame.hex')+'",reference);',tb)
            assert n==1
            (out/'tb.v').write_text(tb)
            (out/'rtl_core.v').write_text((ROOT/'source/ishi_vga_core.v').read_text().replace('module ishi_vga_core','module rtl_core',1))
            subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/'sim.vvp'),str(out/'tb.v'),str(ROOT/'source/ishi_vga_core_pnr.v'),str(ROOT/'source/tr1um_cells.v'),str(out/'rtl_core.v'),str(ROOT/'source/ishi_logo.v')],check=True)
            with (out/'simulation.log').open('w') as log:subprocess.run(['vvp',str(out/'sim.vvp')],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
            assert 'PASS: 128 continuous' in (out/'simulation.log').read_text()
            assert (out/'observed.bin').read_bytes()==(ROOT/'verification/functional/observed.bin').read_bytes()
            results={'rtl-gates':{'status':'PASS','frames':128,'ticks':6720000}}
        (out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
