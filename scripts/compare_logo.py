"""Deterministic resolution/color experiment, not an AI reconstruction.
Run: python3 scripts/compare_logo.py (Pillow, numpy required).
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'samples'
OUT.mkdir(exist_ok=True)
source = Image.open(ROOT / 'assets/ishikai_icon.png').convert('RGB')
# Six dominant flat colors of the supplied image; antialiased edges are quantized.
palette = np.array([[255,255,255], [125,166,250], [220,95,95],
                    [125,200,250], [64,64,255], [128,128,255]], dtype=np.uint8)
# Deliberately preserve distinctions between the four wiring colors at 2 bits/channel.
rgb222 = np.array([[255,255,255], [85,170,255], [255,85,85],
                   [85,255,255], [85,85,255], [170,170,255]], dtype=np.uint8)
rgb111 = np.array([[255,255,255], [0,0,255], [255,0,0],
                   [0,255,255], [0,0,255], [0,0,255]], dtype=np.uint8)
mono = np.array([[255,255,255]] + [[0,0,0]]*5, dtype=np.uint8)
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)

def indices(size):
    a = np.asarray(source.resize(size, Image.Resampling.BOX)).astype(np.int32)
    return ((a[:,:,None,:] - palette.astype(np.int32))**2).sum(axis=3).argmin(axis=2).astype(np.uint8)

def rectangles(a):
    """Merge identical horizontal colored runs on adjacent rows; white is default."""
    active, result = {}, []
    for y in range(a.shape[0]+1):
        runs = []
        if y < a.shape[0]:
            row = a[y]
            edges = np.r_[0, np.where(row[1:] != row[:-1])[0]+1, len(row)]
            runs = [(int(row[x0]), int(x0), int(x1)) for x0,x1 in zip(edges[:-1],edges[1:]) if row[x0]]
        current = set(runs)
        for key in list(active):
            if key not in current:
                c,x0,x1 = key
                result.append([c,x0,active.pop(key),x1,y])
        for key in current:
            active.setdefault(key,y)
    check = np.zeros_like(a)
    for c,x0,y0,x1,y1 in result:
        check[y0:y1,x0:x1] = c
    assert np.array_equal(check,a)
    return sorted(result)

def preview(a, p=palette, size=(512,434)):
    return Image.fromarray(p[a]).resize(size, Image.Resampling.NEAREST)

sizes = [(32,27),(48,41),(64,54),(96,81),(128,108),(160,136)]
sheet = Image.new('RGB',(1120,1510),'#e9edf2')
d = ImageDraw.Draw(sheet)
d.text((20,12),'ISHI logo: resolution study | same display size | 6-color indexed',font=font,fill='black')
d.text((20,39),'BOX downsample -> nearest palette, no dithering -> nearest-neighbor enlargement',font=small,fill='black')
stats = []
for i,(w,h) in enumerate(sizes):
    a = indices((w,h))
    rs = rectangles(a)
    Image.fromarray(palette[a]).save(OUT / f'logo_{w}x{h}_palette.png')
    (OUT / f'logo_{w}x{h}_rectangles.json').write_text(json.dumps(rs,indent=2)+'\n')
    x,y = 20+(i%2)*560, 75+(i//2)*475
    sheet.paste(preview(a),(x,y+30))
    d.text((x,y),f'{w} x {h} | {w*h*3:,} raw bits | {len(rs)} rectangles',font=font,fill='black')
    stats.append(dict(width=w,height=h,raw_index_bits=w*h*3,rectangles=len(rs),
                      unique_rows=len(np.unique(a,axis=0)),
                      x_boundaries=len(set(r[k] for r in rs for k in (1,3))),
                      y_boundaries=len(set(r[k] for r in rs for k in (2,4)))))
sheet.save(OUT/'resolution_comparison.png')

a = indices((64,54))
colors = Image.new('RGB',(1120,1020),'#e9edf2')
d=ImageDraw.Draw(colors)
d.text((20,12),'64 x 54 logo | color / output-pin tradeoff',font=font,fill='black')
for i,(label,p) in enumerate([('6 original colors / external fixed palette',palette),
                             ('RGB222: 6 outputs / chosen 6-color palette',rgb222),
                             ('RGB111: 3 outputs / red + blue + cyan',rgb111),
                             ('Monochrome: 1 output / overlapping strokes merge',mono)]):
    x,y=20+(i%2)*560,55+(i//2)*475
    colors.paste(preview(a,p),(x,y+30))
    d.text((x,y),label,font=small,fill='black')
    Image.fromarray(p[a]).save(OUT/f'logo_64x54_{["original","rgb222","rgb111","mono"][i]}.png')
colors.save(OUT/'color_comparison.png')

for w,h,scale in [(32,27,16),(64,54,8),(96,81,4),(128,108,4)]:
    a=indices((w,h))
    screen=Image.new('RGB',(640,480),'white')
    screen.paste(preview(a,rgb222,(w*scale,h*scale)),((640-w*scale)//2,(480-h*scale)//2))
    screen.save(OUT/f'vga_{w}x{h}_scale{scale}.png')
(OUT/'metrics.json').write_text(json.dumps(stats,indent=2)+'\n')
print(json.dumps(stats,indent=2))

# Geometric tracing of the flat-color logo (approximation, deliberately removes AA).
# Ordered layers: dark/purple buses, light blue traces, red letters, cyan buses.
geometry = [
 (4,36,180,549,221), (5,36,275,360,315), (5,373,275,549,315),
 (1,9,58,576,86), (1,9,410,576,437),
 (1,117,86,131,207), (1,333,86,347,207), (1,387,86,401,207),
 (1,49,193,63,302), (1,49,289,212,302), (1,117,302,144,410),
 (1,184,193,279,207), (1,265,193,279,396), (1,265,382,347,396),
 (1,333,289,347,396), (1,387,289,401,410),
 (1,454,99,468,302), (1,454,99,536,112), (1,522,99,536,261),
 (1,454,289,481,302), (1,522,289,536,410),
 (2,63,140,117,167), (2,77,167,103,329), (2,63,329,117,356),
 (2,144,140,252,167), (2,144,167,171,261), (2,171,234,252,261),
 (2,225,261,252,329), (2,144,329,252,356),
 (2,293,140,320,356), (2,320,234,414,261), (2,414,140,441,356),
 (2,468,140,522,167), (2,481,167,508,329), (2,468,329,522,356),
 (3,9,126,576,140), (3,9,356,576,369),
]
vector_sheet = Image.new('RGB',(1120,1020),'#e9edf2')
d=ImageDraw.Draw(vector_sheet)
d.text((20,12),'37 layered rectangles | snapped geometry (approximate tracing, no edge antialiasing)',font=font,fill='black')
for i,(w,h) in enumerate([(32,27),(48,41),(64,54),(128,108)]):
    a=np.zeros((h,w),dtype=np.uint8)
    rs=[]
    for c,x0,y0,x1,y1 in geometry:
        xx0,xx1=round(x0*w/591),round(x1*w/591)
        yy0,yy1=round(y0*h/501),round(y1*h/501)
        if xx0 == xx1 or yy0 == yy1:
            continue  # At 32x27 five thin rectangles disappear on the sampling grid.
        rs.append([c,xx0,yy0,xx1,yy1])
        a[yy0:yy1,xx0:xx1]=c
    x,y=20+(i%2)*560,55+(i//2)*475
    vector_sheet.paste(preview(a,rgb222),(x,y+30))
    d.text((x,y),f'{w} x {h} | {len(rs)} visible rectangles | RGB222',font=font,fill='black')
    Image.fromarray(rgb222[a]).save(OUT/f'geometry_{w}x{h}.png')
    (OUT/f'geometry_{w}x{h}.json').write_text(json.dumps(rs,indent=2)+'\n')
    if w in (64,128):
        scale=8 if w==64 else 4
        screen=Image.new('RGB',(640,480),'white')
        screen.paste(preview(a,rgb222,(w*scale,h*scale)),((640-w*scale)//2,(480-h*scale)//2))
        screen.save(OUT/f'vga_geometry_{w}x{h}.png')
vector_sheet.save(OUT/'geometry_comparison.png')
