#!/usr/bin/env python3
"""Explicit black-background alternative: unpainted/blanking pixels both black."""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image
from half_slot_trial import ROOT, tb

ap=argparse.ArgumentParser();ap.add_argument('source');ap.add_argument('name');a=ap.parse_args()
src=ROOT/'experiments'/a.source;dst=ROOT/'experiments'/a.name
assert a.name.startswith('a_half_') and '/' not in a.source+a.name and not dst.exists()
for sub in ('build','tests'):(dst/sub).mkdir(parents=True,exist_ok=True)
settings=json.loads((src/'trial.json').read_text());settings['background']='black';settings['source']=a.source
(dst/'trial.json').write_text(json.dumps(settings,indent=2)+'\n')
logo=(src/'ishi_logo.v').read_text()
assert " : 3'd7;" in logo or " : 3'b111;" in logo
logo=logo.replace(" : 3'd7;"," : 3'd0;").replace(" : 3'b111;"," : 3'b000;")
(dst/'ishi_logo.v').write_text(logo)
core=(src/'ishi_vga_core.v').read_text()
assert "active ? logo_rgb : 3'b000" in core
core=core.replace("active ? logo_rgb : 3'b000",'logo_rgb')
core=re.sub(r'^wire active=.*?;\n','',core,flags=re.M)
(dst/'ishi_vga_core.v').write_text(core)
frame=np.array([int(s,16) for s in (src/'tests/expected_frame.hex').read_text().split()],dtype=np.uint8)
frame[(frame&7)==7] &= 24
(dst/'tests/expected_frame.hex').write_text(''.join(f'{x:02x}\n' for x in frame))
screen=frame.reshape((525,settings['horizontal_total']))[:480,:640//settings['scale']]
rgb=np.stack([((screen>>i)&1)*255 for i in (2,1,0)],axis=-1)
Image.fromarray(np.repeat(rgb,settings['scale'],axis=1)).save(dst/'build/reference.png')
(dst/'tests/tb_rtl.v').write_text(tb(settings,'dut.h=0; dut.v=0;'))
cfg=(src/'config.py').read_text().replace(str(src/'tests/tb_rtl.v'),str(dst/'tests/tb_rtl.v'))
cfg=re.sub(r'^HALF_SLOT = .*$',f'HALF_SLOT = {settings!r}',cfg,flags=re.M)
(dst/'config.py').write_text(cfg)
paths=[Path(__file__),ROOT/'scripts/half_slot_trial.py',src/'source_manifest.json',src/'tests/expected_frame.hex',
       *[dst/p for p in ['config.py','trial.json','ishi_vga_core.v','ishi_logo.v','tests/tb_rtl.v','tests/expected_frame.hex']]]
(dst/'source_manifest.json').write_text(json.dumps({'scope':'unadopted black background alternative','sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},indent=2)+'\n')
print(dst)
