#!/usr/bin/env python3
"""Alternative exact RGB111/black A renderers; geometry is never changed."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
import numpy as np
from half_slot_trial import ROOT, tb


def spans(values):
    start=0
    for end in range(1,len(values)+1):
        if end==len(values) or values[end]!=values[start]:
            yield start,end,values[start];start=end


def expression(e):
    if e.is_zero():return "1'b0"
    if e.is_one():return "1'b1"
    if str(e).startswith('Or('):return '('+' | '.join(expression(x) for x in e.xs)+')'
    if str(e).startswith('And('):return '('+' & '.join(expression(x) for x in e.xs)+')'
    return str(e)


def generate(mode):
    src=ROOT/'experiments/a_half_a143_x';dst=ROOT/'experiments'/('a_half_a_bitmap_'+mode)
    assert not dst.exists()
    for sub in ('build','tests'):(dst/sub).mkdir(parents=True,exist_ok=True)
    source=ROOT/'assets/logo_rectangles_a_corrected.json';rects=json.loads(source.read_text())
    im=np.zeros((128,128),dtype=np.uint8)
    for co,a,b,c,d in rects:im[b+3:d+3,128-c:128-a]=[0,3,4,3,1,5][co]
    settings=json.loads((src/'trial.json').read_text());settings.update(renderer=mode)
    (dst/'trial.json').write_text(json.dumps(settings,indent=2)+'\n')
    sys.path.insert(0,str(ROOT/'.tools/logic_pyeda'))
    from pyeda.inter import exprvars,truthtable,espresso_tts
    hv=exprvars('h',7);yv=exprvars('y',7)
    def table_expr(inputs,values):return espresso_tts(truthtable(inputs,values))[0]
    lines=['`default_nettype none','module ishi_logo(input wire [6:0] h,y, output wire [2:0] rgb);']
    stats={}
    if mode in ['rowcode','rowgray']:
        unique=[];ids=[]
        for row in im:
            t=tuple(row.tolist())
            if t not in unique:unique.append(t)
            ids.append(unique.index(t))
        codes=[i^(i>>1) if mode=='rowgray' else i for i in range(len(unique))]
        bits=max(1,max(codes).bit_length());cv=exprvars('c',bits)
        lines.append(f'wire [{bits-1}:0] c;')
        enc=espresso_tts(*[truthtable(yv,''.join(str((codes[i]>>bit)&1) for i in ids)) for bit in range(bits)])
        for bit,e in enumerate(enc):lines.append(f'assign c[{bit}]={expression(e)};')
        tables=[['-']*(128*(1<<bits)) for _ in range(3)]
        for code,row in zip(codes,unique):
            for h,value in enumerate(row):
                for bit in range(3):tables[bit][(code<<7)|h]=str((value>>bit)&1)
        dec=espresso_tts(*[truthtable([*hv,*cv],''.join(t)) for t in tables])
        for bit,e in enumerate(dec):lines.append(f'assign rgb[{bit}]={expression(e)};')
        stats.update(unique_rows=len(unique),row_codes=codes)
    elif mode=='tt':
        dec=espresso_tts(*[truthtable([*hv,*yv],''.join(str((int(p)>>bit)&1) for p in im.flat)) for bit in range(3)])
        for bit,e in enumerate(dec):lines.append(f'assign rgb[{bit}]={expression(e)};')
    elif mode=='rows':
        for bit in range(3):
            groups={}
            for y,row in enumerate((im>>bit)&1):
                key=tuple(row.tolist())
                if any(key):groups.setdefault(key,[]).append(y)
            terms=[]
            for i,(row,ys) in enumerate(groups.items()):
                ex=table_expr(hv,''.join(map(str,row)))
                ey=table_expr(yv,''.join('1' if y in ys else '0' for y in range(128)))
                lines.append(f'wire pat_{bit}_{i}={expression(ex)};')
                lines.append(f'wire sel_{bit}_{i}={expression(ey)};')
                terms.append(f'(pat_{bit}_{i} & sel_{bit}_{i})')
            lines.append(f'assign rgb[{bit}]='+' | '.join(terms)+';')
            stats[f'bit{bit}_rows']=len(groups)
    elif mode in ['setclear','toggle']:
        ports='output wire [2:0] toggle_bits' if mode=='toggle' else 'output wire [2:0] set_bits,clear_bits'
        lines[1]='module ishi_logo(input wire [6:0] h,y, '+ports+');'
        for bit in range(3):
            plane=(im>>bit)&1
            previous=np.zeros_like(plane);previous[:,:127]=plane[:,1:]
            outputs={'toggle_bits':plane^previous} if mode=='toggle' else {'set_bits':plane & (1-previous),'clear_bits':(1-plane)&previous}
            for label,p in outputs.items():
                groups={}
                for h in range(128):
                    col=tuple(p[:,h].tolist())
                    if any(col):groups.setdefault(col,[]).append(h)
                terms=[]
                for i,(col,hs) in enumerate(groups.items()):
                    ex=table_expr(hv,''.join('1' if h in hs else '0' for h in range(128)))
                    ey=table_expr(yv,''.join(map(str,col)))
                    terms.append('('+expression(ex)+' & '+expression(ey)+')')
                lines.append(f'assign {label}[{bit}]='+' | '.join(terms)+';')
                stats[label+str(bit)]=len(groups)
    else:raise ValueError(mode)
    lines+=['endmodule','`default_nettype wire','']
    (dst/'ishi_logo.v').write_text('\n'.join(lines))
    core=(src/'ishi_vga_core.v').read_text()
    if mode in ['setclear','toggle']:
        if mode=='toggle':
            core=core.replace('wire [2:0] logo_rgb;','wire [2:0] toggle_bits;').replace('.rgb(logo_rgb)','.toggle_bits(toggle_bits)')
            update='{r,g,b} ^ toggle_bits'
        else:
            core=core.replace('wire [2:0] logo_rgb;','wire [2:0] set_bits,clear_bits;').replace('.rgb(logo_rgb)','.set_bits(set_bits),.clear_bits(clear_bits)')
            update='({r,g,b} | set_bits) & ~clear_bits'
        core=core.replace("h[7] ? 3'b000 : logo_rgb", "h[7] ? 3'b000 : ("+update+")")
    (dst/'ishi_vga_core.v').write_text(core)
    for f in ['tests/expected_frame.hex','build/reference.png']:(dst/f).write_bytes((src/f).read_bytes())
    (dst/'tests/tb_rtl.v').write_text(tb(settings,'dut.h=0; dut.v=0;'))
    cfg=(src/'config.py').read_text().replace(str(src/'tests/tb_rtl.v'),str(dst/'tests/tb_rtl.v'))
    cfg=re.sub(r'^HALF_SLOT = .*$',f'HALF_SLOT = {settings!r}',cfg,flags=re.M)
    (dst/'config.py').write_text(cfg)
    paths=[Path(__file__),ROOT/'scripts/half_slot_trial.py',source,src/'source_manifest.json',
           *[dst/p for p in ['config.py','trial.json','ishi_vga_core.v','ishi_logo.v','tests/expected_frame.hex','tests/tb_rtl.v']]]
    (dst/'source_manifest.json').write_text(json.dumps({'scope':'exact A geometry, RGB111 black','statistics':stats,
        'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},indent=2)+'\n')
    print(dst.name,stats)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['tt','rows','rowcode','rowgray','setclear','toggle']);a=ap.parse_args()
    generate(a.mode)
