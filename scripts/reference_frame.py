#!/usr/bin/env python3
"""Independent raster reference: ordered rectangle painter, full blanking included."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
rects = json.loads((ROOT/'assets/logo_rectangles.json').read_text())
palette=np.array([63,27,53,31,23,43],dtype=np.uint8)
logo=np.zeros((108,128),dtype=np.uint8)
for c,x0,y0,x1,y1 in rects: logo[y0:y1,x0:x1]=c
screen=np.full((480,160),63,dtype=np.uint8)
screen[24:456,16:144]=np.repeat(palette[logo],4,axis=0)
frame=np.zeros((525,200),dtype=np.uint8)
frame[:480,:160]=screen
frame[:,:164]|=64; frame[:,188:]|=64
frame[:490,:]|=128; frame[492:,:]|=128
(ROOT/'tests/expected_frame.hex').write_text('\n'.join(f'{v:02x}' for v in frame.flat)+'\n')
def rgb(a):
    return np.stack([((a>>4)&3)*85,((a>>2)&3)*85,(a&3)*85],axis=-1)
(ROOT/'build').mkdir(exist_ok=True)
preview = Image.fromarray(np.repeat(rgb(screen),4,axis=1))
# User selected B from the previously rendered proposal sheet. Freeze its pixels.
approved = Image.open(ROOT/'samples/reduced_rectangles/B_outline_bars.png').convert('RGB')
assert np.array_equal(np.asarray(preview), np.asarray(approved)), 'Active design differs from approved B'
preview.save(ROOT/'build/reference_frame.png')
print('Reference: 105000 ticks, 480 active lines, HS=24 ticks, VS=2 lines.')
