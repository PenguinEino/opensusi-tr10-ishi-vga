#!/usr/bin/env python3
"""Design-config-only routing comparison on a frozen proposal placement."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
from a_row_placement import ROOT,route
from check_toolchain import verify


def main():
    ap=argparse.ArgumentParser();ap.add_argument('key',choices=['y1','power']);ap.add_argument('--prl',type=int,required=True)
    ap.add_argument('--span-pack',action='store_true');a=ap.parse_args();verify()
    src=ROOT/'experiments'/f'a_metal_g_{a.key}_anneal4'
    dst=ROOT/'experiments'/f'a_metal_g_{a.key}_route_p{a.prl}{"s" if a.span_pack else ""}'
    assert not dst.exists()
    for sub in ['build','out','tests','layout']:(dst/sub).mkdir(parents=True,exist_ok=True)
    for f in ['ishi_vga_core.v','ishi_logo.v','out/ishi_vga_core_pnr.v','tests/expected_frame.hex','layout/row_assignment.json']:
        shutil.copyfile(src/f,dst/f)
    shutil.copytree(src/'layout/step4',dst/'layout/step4')
    knobs={'PRL_MIN_PINS':a.prl,'SPAN_LANE_PACK':a.span_pack}
    cfg,n=re.subn(r'^ROUTING_KNOBS = .*$',f'ROUTING_KNOBS = {knobs!r}',(src/'config.py').read_text(),flags=re.M);assert n==1
    (dst/'config.py').write_text(cfg)
    paths=[Path(__file__),ROOT/'scripts/a_row_placement.py',src/'source_manifest.json',src/'layout/placement.json',
           dst/'config.py',dst/'out/ishi_vga_core_pnr.v',dst/'layout/row_assignment.json',*sorted((dst/'layout/step4').glob('*'))]
    (dst/'source_manifest.json').write_text(json.dumps({'source':src.name,'knobs':knobs,
        'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},indent=2)+'\n')
    route(dst)


if __name__=='__main__':main()
