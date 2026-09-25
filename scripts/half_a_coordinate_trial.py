#!/usr/bin/env python3
"""Exact corrected A geometry, RGB111/black; aligned 7-bit logo coordinates.

H starts at 143: the entire 128-wide logo is h=127..0, selected by !h[7].
V keeps the proven 500..1023,0 cycle. Its folded y=v[8:2] is safe because
the only repeated reachable y values lie outside every colored rectangle.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from half_slot_trial import ROOT, tb


def generate(axis, direct):
    name=f'a_half_a143_{axis}'+('_direct' if direct else '')
    dst=ROOT/'experiments'/name;src=ROOT/'experiments/a_half_a128_black'
    assert not dst.exists()
    for sub in ('build','tests'):(dst/sub).mkdir(parents=True,exist_ok=True)
    source=ROOT/'assets/logo_rectangles_a_corrected.json'
    rects=json.loads(source.read_text())
    settings=json.loads((src/'trial.json').read_text())
    settings.update(h_start=143,h_end=200,coordinate_mode='H143, h[6:0], v[8:2], !h[7] logo select',
                    group_axis=axis,direct_color=direct)
    (dst/'trial.json').write_text(json.dumps(settings,indent=2)+'\n')
    def raw(v,a,b):
        if a==0:return f"({v} < 7'd{b})" if b<128 else "1'b1"
        if b==128:return f"({v} >= 7'd{a})"
        return f"(({v} >= 7'd{a}) && ({v} < 7'd{b}))"
    def interval(v,a,b):
        return raw('h',128-b,128-a) if v=='h' else raw('y',a+3,b+3)
    lines=['`default_nettype none','module ishi_logo(input wire [6:0] h,y, output wire [2:0] rgb);']
    for co in [4,5,1,2,3]:
        groups={}
        for c,a,b,d,e in rects:
            if c!=co:continue
            key,value=((a,d),(b,e)) if axis=='x' else ((b,e),(a,d))
            groups.setdefault(key,[]).append(value)
        first,second=('h','y') if axis=='x' else ('y','h')
        terms=['('+interval(first,*k)+' & ('+' | '.join(interval(second,*v) for v in values)+'))' for k,values in groups.items()]
        lines.append(f'wire color_{co} = '+' |\n'.join(terms)+';')
    if direct:
        lines += ['wire cyan=color_1 | color_3;',
                  'assign rgb[2]=color_2 | (color_5 & ~color_1);',
                  'assign rgb[1]=cyan & ~color_2;',
                  'assign rgb[0]=(cyan | color_4 | color_5) & ~color_2;']
        # Independent truth check of the geometric exclusions behind this form.
        for yy in range(108):
            for xx in range(128):
                hits={c:any(co==c and a<=xx<d and b<=yy<e for co,a,b,d,e in rects) for c in [1,2,3,4,5]}
                color=0
                for co,a,b,d,e in rects:
                    if a<=xx<d and b<=yy<e:color=[0,3,4,3,1,5][co]
                red=hits[2] or (hits[5] and not hits[1]);cyan=hits[1] or hits[3]
                value=(int(red)<<2)|(int(cyan and not hits[2])<<1)|int((cyan or hits[4] or hits[5]) and not hits[2])
                assert value==color,(xx,yy)
    else:
        lines.append("assign rgb=color_3 ? 3'd3 : color_2 ? 3'd4 : color_1 ? 3'd3 : color_5 ? 3'd5 : color_4 ? 3'd1 : 3'd0;")
    lines += ['endmodule','`default_nettype wire','']
    (dst/'ishi_logo.v').write_text('\n'.join(lines))
    core=(src/'ishi_vga_core.v').read_text()
    replacements={'.h(h),.y(v[9:2])':'.h(h[6:0]),.y(v[8:2])',
                  "h == 8'd120":"h == 8'd200","h <= 8'd63":"h <= 8'd143",
                  "((h >= 8'd132) && (h < 8'd156))":"((h >= 8'd212) && (h < 8'd236))",
                  '{r,g,b} <= logo_rgb;':"{r,g,b} <= h[7] ? 3'b000 : logo_rgb;"}
    for a,b in replacements.items():assert a in core;core=core.replace(a,b)
    (dst/'ishi_vga_core.v').write_text(core)
    for f in ['tests/expected_frame.hex','build/reference.png']:(dst/f).write_bytes((src/f).read_bytes())
    (dst/'tests/tb_rtl.v').write_text(tb(settings,'dut.h=0; dut.v=0;'))
    cfg=(src/'config.py').read_text().replace(str(src/'tests/tb_rtl.v'),str(dst/'tests/tb_rtl.v'))
    cfg=re.sub(r'^HALF_SLOT = .*$',f'HALF_SLOT = {settings!r}',cfg,flags=re.M)
    (dst/'config.py').write_text(cfg)
    paths=[Path(__file__),ROOT/'scripts/half_slot_trial.py',source,src/'source_manifest.json',src/'ishi_vga_core.v',
           *[dst/p for p in ['config.py','trial.json','ishi_vga_core.v','ishi_logo.v','tests/expected_frame.hex','tests/tb_rtl.v']]]
    (dst/'source_manifest.json').write_text(json.dumps({'scope':'exact corrected A geometry with RGB111/black background; seven terminals excluding VSS',
        'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},indent=2)+'\n')
    print(name)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('axis',choices=['x','y']);ap.add_argument('--direct',action='store_true');a=ap.parse_args()
    generate(a.axis,a.direct)
