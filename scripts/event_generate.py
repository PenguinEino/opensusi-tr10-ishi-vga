#!/usr/bin/env python3
"""Generate isolated B-image event-driven RGB register experiments."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECTS = json.loads((ROOT / 'assets/logo_rectangles.json').read_text())
PALETTE = [63, 27, 53, 31, 23, 43]

def raster():
    # Match reference_frame.py's ordered painter, then expand to screen coords.
    logo = [[0] * 128 for _ in range(108)]
    for color, x0, y0, x1, y1 in RECTS:
        for y in range(y0, y1):
            for x in range(x0, x1): logo[y][x] = color
    return [[63 if x < 16 or x >= 144 or y < 6 or y >= 114 else PALETTE[logo[y-6][x-16]]
             for x in range(160)] for y in range(120)]

def intervals(rows):
    out=[]
    if not rows: return out
    a=prev=rows[0]
    for y in rows[1:]:
        if y != prev+1: out.append((a,prev+1)); a=y
        prev=y
    out.append((a,prev+1))
    return out

def ycond(ranges):
    terms=[]
    for a,b in ranges:
        if b-a==1: terms.append(f"(y == 8'd{a})")
        else: terms.append(f"((y >= 8'd{a}) && (y < 8'd{b}))")
    return ' | '.join(terms) if terms else "1'b0"

def gen(kind, offset):
    img=raster()
    # Group identical transition sets so each horizontal comparison is shared.
    groups={}
    for h in range(1,160):
        bymask={}
        for bit in range(6):
            rows=[y for y in range(120) if ((img[y][h]>>bit)&1)!=((img[y][h-1]>>bit)&1)]
            if not rows: continue
            ys=intervals(rows)
            if kind=='toggle': key=('toggle',tuple(ys))
            else:
                rising=[y for y in rows if (img[y][h]>>bit)&1]
                falling=[y for y in rows if not ((img[y][h]>>bit)&1)]
                for direction, rr in [('set',rising),('clear',falling)]:
                    if rr:
                        key=(direction,tuple(intervals(rr)))
                        groups.setdefault((h,key),0)
                        groups[(h,key)] |= 1<<bit
                continue
            groups.setdefault((h,key),0); groups[(h,key)] |= 1<<bit
    decl=[]; set_terms=[]; clear_terms=[]; toggle_terms=[]
    for i,((h,key),mask) in enumerate(sorted(groups.items(),key=lambda q:(q[0][0],q[0][1]))):
        direction,ranges=key
        cond=f"((h == 8'd{(h+offset)%256}) && ({ycond(ranges)}))"
        decl.append(f"    wire ev_{i} = {cond};")
        if direction=='set': set_terms.append(f"({{6{{ev_{i}}}}} & 6'd{mask})")
        elif direction=='clear': clear_terms.append(f"({{6{{ev_{i}}}}} & 6'd{mask})")
        else: toggle_terms.append(f"({{6{{ev_{i}}}}} & 6'd{mask})")
    core='''`timescale 1ns/1ps
`default_nettype none
module ishi_vga_core(input wire clk,input wire reset_n,output reg [1:0] r,output reg [1:0] g,output reg [1:0] b,output reg hsync,output reg vsync);
    (* async_reg = "true" *) reg [1:0] reset_pipe;
    always @(posedge clk or negedge reset_n)
        if (!reset_n) reset_pipe <= 2'b00; else reset_pipe <= {reset_pipe[0],1'b1};
    wire running=reset_pipe[1];
    reg [7:0] h; reg [9:0] v;
    wire [7:0] y=v[9:2];
'''
    core+='\n'.join(decl)+'\n'
    core+='    wire [5:0] set_mask = '+' | '.join(set_terms or ["6'd0"])+';\n'
    core+='    wire [5:0] clear_mask = '+' | '.join(clear_terms or ["6'd0"])+';\n'
    core+='    wire [5:0] toggle_mask = '+' | '.join(toggle_terms or ["6'd0"])+';\n'
    core+='''    wire line_start=(h==8'd'''+str(offset)+''');
    wire line_end=(h==8'd'''+str((160+offset)%256)+''');
    wire active=(v<10'd480);
    wire hs_low='''+ (f"((h >= 8'd{(164+offset)%256}) || (h < 8'd{(188+offset)%256}))" if (164+offset)%256 > (188+offset)%256 else f"((h >= 8'd{(164+offset)%256}) && (h < 8'd{(188+offset)%256}))") + ''';
    always @(posedge clk or negedge running) begin
      if (!running) begin h<=8'd'''+str(offset)+''' ; v<=0; {r,g,b}<=0; hsync<=1; vsync<=1; end
      else begin
        if (h==8'd'''+str((199+offset)%256)+''') begin h<=8'd'''+str(offset)+'''; v<=(v==10'd524)?10'd0:v+10'd1; end else h<=h+1'b1;
        hsync<=!hs_low; vsync<=!((v>=10'd490)&&(v<10'd492));
        if (!active || line_end) {r,g,b}<=6'd0;
        else if (line_start) {r,g,b}<=6'd63;
        else if (kind_toggle) {r,g,b}<={r,g,b} ^ toggle_mask;
        else {r,g,b}<=({r,g,b} & ~clear_mask) | set_mask;
      end
    end
endmodule
`default_nettype wire
'''
    core=core.replace('kind_toggle',"1'b1" if kind=='toggle' else "1'b0")
    return core

def write(name, kind, offset):
    d=ROOT/'experiments'/f'event_{name}'; d.mkdir(parents=True,exist_ok=True)
    for sub in ('build','tests'): (d/sub).mkdir(exist_ok=True)
    p=d/'tests/expected_frame.hex'
    if not p.exists(): p.symlink_to('../../../tests/expected_frame.hex')
    (d/'ishi_vga_core.v').write_text(gen(kind,offset))
    # Keep the module interface and source list uniform for the existing testbench.
    (d/'ishi_logo.v').write_text('`default_nettype none\nmodule ishi_logo(input wire [7:0] h,input wire [7:0] y,output wire [5:0] rgb); assign rgb=0; endmodule\n`default_nettype wire\n')
    cfg=(ROOT/'config.py').read_text()
    cfg=cfg.replace("SYN_RTL = ['rtl/ishi_vga_core.v', 'rtl/ishi_logo.v']","SYN_RTL = ['ishi_vga_core.v', 'ishi_logo.v']")
    cfg=cfg.replace("SYN_TB_RTL = ['tests/tb_vga.v']",f"SYN_TB_RTL = ['{ROOT}/tests/tb_vga.v']")
    cfg=cfg.replace("SYN_TB_NET = ['tests/tb_vga.v']",f"SYN_TB_NET = ['{ROOT}/tests/tb_vga.v']")
    (d/'config.py').write_text(cfg)

for mode in ('setclear','toggle'):
    for off in (0,80): write(f'{mode}_h{off}', mode, off)
