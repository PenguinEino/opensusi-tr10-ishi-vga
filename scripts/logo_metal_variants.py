#!/usr/bin/env python3
"""B-plus-metal proposal generation; preserves old A/B and pinned dependencies.

Meaning labels refer to the Siliwiz logo's INV/NAND/NOR motifs, not to the VGA
logic. These partial illustrations do not claim to be extracted CMOS layouts.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import numpy as np
from PIL import Image
from half_slot_trial import ROOT, tb

ARTICLE='https://note.com/akira_tsuchiya/n/n0c720b3498b4'
# Half-open coordinates in the 128x108 B logo.
B_NETS={
 'Y1':[[11,42,14,65]],
 'Y2':[[40,42,60,45],[57,42,60,85],[57,82,75,85],[72,62,75,85]],
 # A shorter drain connection than A's four-rectangle cosmetic version.
 'Y3':[[98,21,101,65],[98,21,116,24],[113,21,116,45]],
 # Two PMOS source regions suffice; A's two central VDD drops share diffusion.
 'VDD':[[25,19,28,45],[72,19,75,45]],
 'VSS':[[25,62,28,88],[84,62,87,88],[113,62,116,88]],
}
# Grid variants use logo-relative horizontal clock ticks (8 screen pixels),
# ordinary VGA vertical lines. Horizontal positions refer to the shared glyphs.
G_NETS={
 'Y1':[[2,188,3,316]],
 'Y3':[[50,124,51,316],[50,124,61,132],[60,124,61,188]],
 'VDD':[[14,108,15,188],[40,108,41,188]],
 'VSS':[[14,316,15,396],[41,316,42,396],[60,316,61,396]],
}
CATALOG=[
 ('b_y1','B+1：INVの出力','B',['Y1']),
 ('b_ends','B+4：両端の出力','B',['Y1','Y3']),
 ('b_outputs','B+8：3つの出力','B',['Y1','Y2','Y3']),
 ('b_power','B+5：電源への枝','B',['VDD','VSS']),
 ('g_y1','格子+1：INVの出力','grid',['Y1']),
 ('g_ends','格子+4：両端の出力','grid',['Y1','Y3']),
 ('g_power','格子+5：電源への枝','grid',['VDD','VSS']),
]


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def generate(key):
    entry=next(c for c in CATALOG if c[0]==key)
    _,title,base,nets=entry
    src=ROOT/'experiments'/('a_half_b128_black' if base=='B' else 'a_half_grid64_black')
    dst=ROOT/'experiments'/('a_metal_'+key)
    assert not dst.exists()
    for sub in ['build','tests']: (dst/sub).mkdir(parents=True,exist_ok=True)
    groups=B_NETS if base=='B' else G_NETS
    added=[r for net in nets for r in groups[net]]
    settings=json.loads((src/'trial.json').read_text())
    settings.update(proposal=key,title=title,base=base,added_nets=nets,added_segments=len(added),
        article=ARTICLE,background='black',palette_rgb111=[0,3,4,3,1,5],adopted=False,
        grid_n_diff_split=(base=='grid'),drawing_not_extracted_cmos=True)
    (dst/'trial.json').write_text(json.dumps(settings,ensure_ascii=False,indent=2)+'\n')
    (dst/'metal.json').write_text(json.dumps({net:groups[net] for net in nets},indent=2)+'\n')
    logo=(src/'ishi_logo.v').read_text()
    def raw(v,a,b,bits):
        if a==0:return f"({v} < {bits}'d{b})" if b<1<<bits else "1'b1"
        if b==1<<bits:return f"({v} >= {bits}'d{a})"
        return f"(({v} >= {bits}'d{a}) && ({v} < {bits}'d{b}))"
    if base=='B':
        def h(a,b):
            lo,hi=(64-b)%256,(64-a)%256
            return raw('h',lo,hi,8) if lo<hi else '('+raw('h',lo,256,8)+' | '+raw('h',0,hi,8)+')'
        terms=[f"({h(a,c)} & {raw('y',b+131,d+131,8)})" for a,b,c,d in added]
        logo=logo.replace('wire color_1 =','wire color_1_base =')
        logo=logo.replace('assign rgb =', 'wire metal_add = '+' | '.join(terms)+';\nwire color_1=color_1_base | metal_add;\nassign rgb =')
        # Independent ordered painter in ordinary logo coordinates.
        rects=json.loads((ROOT/'assets/logo_rectangles.json').read_text())
        rectangles=[r for r in rects if r[0] in [4,5,1]]+[[1,*r] for r in added]+[r for r in rects if r[0] in [2,3]]
        pixels=np.zeros((108,128),dtype=np.uint8)
        for co,a,b,c,d in rectangles:pixels[b:d,a:c]=settings['palette_rgb111'][co]
        screen=np.zeros((480,160),dtype=np.uint8)
        screen[24:456,16:144]=np.repeat(pixels,4,axis=0)
    else:
        terms=[f"({raw('h',64-c,64-a,7)} & {raw('v',b+500,d+500,10)})" for a,b,c,d in added]
        logo=logo.replace('wire cyan=','wire cyan_base=')
        logo=logo.replace('wire purple=in_logo',"wire purple=(h!=7'd23) && in_logo")
        logo=logo.replace('assign rgb=', 'wire metal_add='+' | '.join(terms)+';\nwire cyan=cyan_base | metal_add;\nassign rgb=')
        screen=np.zeros((480,80),dtype=np.uint8)
        screen[92:108,8:72]=3;screen[396:412,8:72]=3
        screen[172:204,8:72]=1;screen[300:332,8:72]=5
        screen[300:332,48:49]=0 # separate NAND output from NOR source region
        for a,b,c,d in added:screen[b:d,a+8:c+8]=3
        glyphs=json.loads((ROOT/'experiments/a_half_grid64/glyphs.json').read_text())
        for i,letter in enumerate('ISHI'):
            for row,bits in enumerate(glyphs[letter]):
                for col,on in enumerate(bits):
                    if on=='1':screen[140+row*32:172+row*32,8+i*16+col*2:10+i*16+col*2]=4
    (dst/'ishi_logo.v').write_text(logo)
    (dst/'ishi_vga_core.v').write_bytes((src/'ishi_vga_core.v').read_bytes())
    scale=settings['scale'];ht=settings['horizontal_total']
    frame=np.zeros((525,ht),dtype=np.uint8);frame[:480,:640//scale]=screen
    frame[:,:656//scale]|=8;frame[:,752//scale:]|=8
    frame[:490,:]|=16;frame[492:,:]|=16
    (dst/'tests/expected_frame.hex').write_text(''.join(f'{x:02x}\n' for x in frame.flat))
    rgb=np.stack([((screen>>b)&1)*255 for b in [2,1,0]],axis=-1)
    Image.fromarray(np.repeat(rgb,scale,axis=1)).save(dst/'build/reference.png')
    (dst/'tests/tb_rtl.v').write_text(tb(settings,'dut.h=0; dut.v=0;'))
    cfg=(src/'config.py').read_text().replace(str(src/'tests/tb_rtl.v'),str(dst/'tests/tb_rtl.v'))
    cfg=re.sub(r'^HALF_SLOT = .*$',f'HALF_SLOT = {settings!r}',cfg,flags=re.M)
    (dst/'config.py').write_text(cfg)
    paths=[Path(__file__),ROOT/'scripts/half_slot_trial.py',ROOT/'assets/logo_rectangles.json',
        ROOT/'assets/ishi_logo_siliwiz_source.json',ROOT/'toolchain.lock.json',src/'source_manifest.json',
        *[dst/f for f in ['config.py','trial.json','metal.json','ishi_logo.v','ishi_vga_core.v','tests/expected_frame.hex','tests/tb_rtl.v']]]
    if base=='grid':paths.append(ROOT/'experiments/a_half_grid64/glyphs.json')
    (dst/'source_manifest.json').write_text(json.dumps({'scope':'unadopted B-plus-metal design proposal',
        'sha256':{str(p.relative_to(ROOT)):sha(p) for p in paths}},indent=2)+'\n')
    print(dst.name,title,len(added))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('key',choices=[c[0] for c in CATALOG]);args=ap.parse_args()
    generate(args.key)
