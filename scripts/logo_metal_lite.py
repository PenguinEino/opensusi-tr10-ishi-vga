#!/usr/bin/env python3
"""One added INV drain trace, with the previous grid artwork otherwise intact.

This depicts the INV connection only. It does not add the NAND/NOR diffusion
separation used by the more circuit-literal grid proposals.
"""
import hashlib,json,re
from pathlib import Path
import numpy as np
from PIL import Image
import logo_metal_variants as design


def main():
    key='g_y1_lite'
    design.CATALOG.append((key,'格子+1：INVだけ追加','grid',['Y1']))
    design.generate(key)
    dst=design.ROOT/'experiments'/('a_metal_'+key)
    logo=(dst/'ishi_logo.v').read_text()
    assert "(h!=7'd23) && " in logo
    (dst/'ishi_logo.v').write_text(logo.replace("(h!=7'd23) && ",''))
    settings=json.loads((dst/'trial.json').read_text());settings['grid_n_diff_split']=False
    (dst/'trial.json').write_text(json.dumps(settings,ensure_ascii=False,indent=2)+'\n')
    cfg=(dst/'config.py').read_text()
    cfg=re.sub(r'^HALF_SLOT = .*$',f'HALF_SLOT = {settings!r}',cfg,flags=re.M)
    (dst/'config.py').write_text(cfg)
    f=dst/'tests/expected_frame.hex'
    frame=np.array([int(s,16) for s in f.read_text().split()],dtype=np.uint8).reshape(525,100)
    frame[300:332,48]=(frame[300:332,48]&24)|5
    f.write_text(''.join(f'{v:02x}\n' for v in frame.flat))
    screen=frame[:480,:80]&7
    rgb=np.stack([((screen>>b)&1)*255 for b in [2,1,0]],axis=-1)
    Image.fromarray(np.repeat(rgb,8,axis=1)).save(dst/'build/reference.png')
    p=dst/'source_manifest.json';m=json.loads(p.read_text())
    for relative in list(m['sha256']):
        m['sha256'][relative]=hashlib.sha256((design.ROOT/relative).read_bytes()).hexdigest()
    m['sha256'][str(Path(__file__).relative_to(design.ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    m['parameter_override']={'grid_n_diff_split':False,'meaning':'INV output only; not complete CMOS extraction'}
    p.write_text(json.dumps(m,indent=2)+'\n')


if __name__=='__main__':main()
