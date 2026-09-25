#!/usr/bin/env python3
"""Seven-pad fallback: regularly spaced glyphs, shared I, coarse B-style bars.

This intentionally changes the artwork. It is not an exact A/B optimization.
The reference uses screen coordinates and a human-readable 8x7 glyph table.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from half_slot_trial import ROOT, tb

GLYPHS = {
    'I': ['00111100','00011000','00011000','00011000','00011000','00011000','00111100'],
    'S': ['00111110','01100000','01100000','00111100','00000110','00000110','01111100'],
    'H': ['01100110','01100110','01100110','01111110','01100110','01100110','01100110'],
}


def main():
    d=ROOT/'experiments/a_half_grid64'
    assert not d.exists()
    for sub in ('build','tests'):(d/sub).mkdir(parents=True,exist_ok=True)
    settings={'art':'new grid redraw, shared I; not exact A/B','scale':8,'h_start':71,'h_end':100,'h_bits':7,
              'v_start':500,'v_last':0,'horizontal_total':100,'signals':6,
              'including_vdd_excluding_common_vss':7,'target_bbox_um':[1800,900],'adopted':False,'reset':False}
    (d/'trial.json').write_text(json.dumps(settings,indent=2)+'\n')
    (d/'glyphs.json').write_text(json.dumps(GLYPHS,indent=2)+'\n')
    # Only eight inputs in the glyph decoder: glyph slot, row, column.
    sys.path.insert(0,str(ROOT/'.tools/logic_pyeda'))
    from pyeda.inter import exprvars,And,Or,espresso_exprs
    c=exprvars('c',2);y=exprvars('y',3);x=exprvars('x',3)
    def eq(v,n):return And(*[b if n&(1<<i) else ~b for i,b in enumerate(v)])
    terms=[]
    for char in range(4):
        for yy,row in enumerate(GLYPHS['ISHI'[char]]):
            for xx,on in enumerate(row):
                if on=='1':terms.append(eq(c,char)&eq(y,yy)&eq(x,xx))
    expr=espresso_exprs(Or(*terms).to_dnf())[0]
    def verilog(e):
        if e.is_zero():return "1'b0"
        if e.is_one():return "1'b1"
        if str(e).startswith('Or('):return '('+' | '.join(verilog(t) for t in e.xs)+')'
        if str(e).startswith('And('):return '('+' & '.join(verilog(t) for t in e.xs)+')'
        return str(e)
    logo=f'''`default_nettype none
module ishi_logo(input wire [6:0] h,input wire [9:0] v,output wire [2:0] rgb);
wire [1:0] c=~h[5:4];
wire [2:0] x=~h[3:1];
wire [2:0] y=v[7:5] ^ 3'b100;
wire glyph={verilog(expr)};
wire in_logo=~h[6];
wire red=in_logo && (v>=10'd640) && (v<10'd864) && glyph;
wire cyan=in_logo && ((v[9:4]==6'd37) || (v[9:4]==6'd56));
wire blue=in_logo && (v[9:5]==5'd21);
wire purple=in_logo && (v[9:5]==5'd25);
assign rgb=red ? 3'b100 : cyan ? 3'b011 : blue ? 3'b001 : purple ? 3'b101 : 3'b111;
endmodule
`default_nettype wire
'''
    (d/'ishi_logo.v').write_text(logo)
    core='''`timescale 1ns/1ps
`default_nettype none
module ishi_vga_core(input wire clk,output reg r,g,b,hsync,vsync);
reg [6:0] h;
reg [9:0] v;
wire [2:0] logo_rgb;
ishi_logo u_logo(.h(h),.v(v),.rgb(logo_rgb));
wire active=((h>=7'd120)||(h<7'd72)) && (v>=10'd500) && (v<10'd980);
always @(posedge clk) begin
  if(h==7'd100) begin
    h<=7'd71;
    v<=(v==10'd0) ? 10'd500 : v+10'd1;
  end else h<=h-7'd1;
  hsync<=!((h>=7'd106)&&(h<7'd118));
  vsync<=!((v>=10'd990)&&(v<10'd992));
  {r,g,b}<=active ? logo_rgb : 3'b000;
end
endmodule
`default_nettype wire
'''
    (d/'ishi_vga_core.v').write_text(core)
    screen=np.full((480,80),7,dtype=np.uint8)
    # All intervals below are ordinary VGA screen coordinates, independent of h/v encodings.
    screen[92:108,8:72]=3;screen[396:412,8:72]=3
    screen[172:204,8:72]=1;screen[300:332,8:72]=5
    for char,letter in enumerate('ISHI'):
        for row,bits in enumerate(GLYPHS[letter]):
            for col,on in enumerate(bits):
                if on=='1':screen[140+row*32:172+row*32,8+char*16+col*2:10+char*16+col*2]=4
    frame=np.zeros((525,100),dtype=np.uint8);frame[:480,:80]=screen
    frame[:,:82]|=8;frame[:,94:]|=8;frame[:490,:]|=16;frame[492:,:]|=16
    (d/'tests/expected_frame.hex').write_text(''.join(f'{p:02x}\n' for p in frame.flat))
    rgb=np.stack([((screen>>i)&1)*255 for i in (2,1,0)],axis=-1)
    Image.fromarray(np.repeat(rgb,8,axis=1)).save(d/'build/reference.png')
    (d/'tests/tb_rtl.v').write_text(tb(settings,'dut.h=0; dut.v=0;'))
    cfg=(ROOT/'experiments/a_half_b64_5col/config.py').read_text()
    cfg=cfg.replace(str(ROOT/'experiments/a_half_b64_5col/tests/tb_rtl.v'),str(d/'tests/tb_rtl.v'))
    cfg=re.sub(r'^HALF_SLOT = .*$',f'HALF_SLOT = {settings!r}',cfg,flags=re.M)
    cfg=re.sub(r'^N_ROWS = .*$', 'N_ROWS = 3',cfg,flags=re.M)
    cfg=re.sub(r'^CH_HEIGHTS = .*$', 'CH_HEIGHTS = [140.4] + [151.2] * 2 + [162.0]',cfg,flags=re.M)
    cfg=re.sub(r'^ROUTE_CH_HEIGHTS = .*$', 'ROUTE_CH_HEIGHTS = [216.0] + [900.0] * 2 + [216.0]',cfg,flags=re.M)
    (d/'config.py').write_text(cfg)
    paths=[Path(__file__),ROOT/'scripts/half_slot_trial.py',ROOT/'toolchain.lock.json',
           *[d/p for p in ['config.py','trial.json','glyphs.json','ishi_vga_core.v','ishi_logo.v','tests/tb_rtl.v','tests/expected_frame.hex']]]
    (d/'source_manifest.json').write_text(json.dumps({'scope':'unadopted grid redraw, 7 pads','sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},indent=2)+'\n')
    print(d)


if __name__=='__main__':main()
