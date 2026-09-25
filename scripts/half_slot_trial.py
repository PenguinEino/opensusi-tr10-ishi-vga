#!/usr/bin/env python3
"""Isolated seven-pad trials: VDD + CLK + HS/VS + RGB111; VSS common.

No reset or ring oscillator. Initialization is TESTBENCH ONLY. Artwork changes
are explicit alternatives, never overwrites of the accepted A/B sources.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PALETTE = [7, 3, 4, 3, 1, 5]  # white, cyan, red, cyan, blue, magenta


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tb(settings, initializer):
    n = settings['horizontal_total'] * 525
    half = settings['scale'] / 25.2 * 500
    return f'''`timescale 1ns/1ps
module tb_vga;
reg clk=0;
wire r,g,b,hsync,vsync;
ishi_vga_core dut(.clk(clk),.r(r),.g(g),.b(b),.hsync(hsync),.vsync(vsync));
real half_period={half:.12f};
initial begin
  if ($value$plusargs("HALF_NS=%f",half_period)) begin end
  forever #(half_period) clk=~clk;
end
reg [4:0] expected[0:{n-1}];
integer i,idx,fd,tries;
reg prev_vs;
initial begin
  // Test fixture only: the ASIC has NO initialized state or reset port.
  {initializer}
  $readmemh("tests/expected_frame.hex",expected);
  repeat ({2*n}) begin @(posedge clk); #35; end
  prev_vs=vsync;
  tries=0;
  begin : seek
    forever begin
      @(posedge clk); #35;
      tries=tries+1;
      if (prev_vs===1'b1 && vsync===1'b0) disable seek;
      if (tries>{n}) $fatal(1,"FAIL: no VSYNC after startup");
      prev_vs=vsync;
    end
  end
  idx={490*settings['horizontal_total']};
  fd=$fopen("build/observed.hex","w");
  for(i=0;i<{2*n};i=i+1) begin
    if ({{vsync,hsync,r,g,b}} !== expected[idx])
      $fatal(1,"FAIL: tick=%0d idx=%0d got=%h expected=%h",i,idx,{{vsync,hsync,r,g,b}},expected[idx]);
    if(i<{n}) $fdisplay(fd,"%02x",{{vsync,hsync,r,g,b}});
    idx=(idx+1)%{n};
    @(posedge clk); #35;
  end
  $fclose(fd);
  $display("PASS: {2*n} pixel ticks, reset-free acquisition and two exact frames");
  $finish;
end
initial begin #300000000; $fatal(1,"FAIL: watchdog"); end
endmodule
'''


def generate(art, scale):
    assert scale in (4, 8, 16)
    name = f'a_half_{art.lower()}{512//scale}_5col'
    d = ROOT / 'experiments' / name
    assert not d.exists(), 'Do not overwrite trials'
    for sub in ('build', 'tests'): (d/sub).mkdir(parents=True, exist_ok=True)
    source = ROOT/'assets'/('logo_rectangles_a_corrected.json' if art == 'A' else 'logo_rectangles.json')
    factor = scale//4
    rects = [[c, *[(x+factor//2)//factor for x in xy]] for c,*xy in json.loads(source.read_text())]
    # At 32x27, round thin strokes to at least one logical pixel explicitly.
    for r in rects:
        r[3]=max(r[3],r[1]+1);r[4]=max(r[4],r[2]+1)
    hw=(800//scale-1).bit_length(); yw=10-(scale.bit_length()-1)
    hstart=79 if art=='B' and scale==4 else (1 << (hw-2))-1
    vstart=500 if scale==4 else 488
    ht=800//scale; hend=(hstart-ht+1)%(1<<hw)
    vlast=(vstart+524)%1024
    settings={'art':art,'scale':scale,'h_start':hstart,'h_end':hend,'h_bits':hw,
              'v_start':vstart,'v_last':vlast,'horizontal_total':ht,
              'palette_rgb111':PALETTE,'signals':6,'including_vdd_excluding_common_vss':7,
              'target_bbox_um':[1800,900],'adopted':False,'reset':False}
    (d/'trial.json').write_text(json.dumps(settings,indent=2)+'\n')
    (d/'rectangles.json').write_text(json.dumps(rects,indent=2)+'\n')

    def raw(axis,lo,hi,bits):
        if lo==hi:return "1'b0"
        if lo==0 and hi==1<<bits:return "1'b1"
        if lo==0:return f"({axis} < {bits}'d{hi})"
        if hi==1<<bits:return f"({axis} >= {bits}'d{lo})"
        return f"(({axis} >= {bits}'d{lo}) && ({axis} < {bits}'d{hi}))"
    def hor(a,b):
        lo,hi=(hstart-b+1)%(1<<hw),(hstart-a+1)%(1<<hw)
        if lo<hi:return raw('h',lo,hi,hw)
        return '('+raw('h',lo,1<<hw,hw)+' | '+raw('h',0,hi,hw)+')'
    def interval(axis,a,b):
        return hor(a+64//scale,b+64//scale) if axis=='h' else raw('y',a+(vstart+24)//scale,b+(vstart+24)//scale,yw)
    assert (vstart+24)%scale==0
    axis='h' if art=='A' else 'y'
    lines=['`default_nettype none',f'module ishi_logo(input wire [{hw-1}:0] h, input wire [{yw-1}:0] y, output wire [2:0] rgb);']
    for color in [4,5,1,2,3]:
        groups={}
        for co,a,b,c,e in rects:
            if co!=color:continue
            k,val=((a,c),(b,e)) if axis=='h' else ((b,e),(a,c))
            groups.setdefault(k,[]).append(val)
        other='y' if axis=='h' else 'h'
        terms=['('+interval(axis,*k)+' & ('+' | '.join(interval(other,*v) for v in vals)+'))' for k,vals in groups.items()]
        lines.append(f'wire color_{color} = '+' |\n'.join(terms)+';')
    lines.append('assign rgb = '+' : '.join(f"color_{c} ? 3'd{PALETTE[c]}" for c in [3,2,1,5,4])+" : 3'd7;")
    lines+=['endmodule','`default_nettype wire','']
    (d/'ishi_logo.v').write_text('\n'.join(lines))
    core=f'''`timescale 1ns/1ps
`default_nettype none
// Reset-free trial. No FPGA power-on initialization is synthesized.
module ishi_vga_core(input wire clk, output reg r,g,b,hsync,vsync);
reg [{hw-1}:0] h;
reg [9:0] v;
wire [2:0] logo_rgb;
ishi_logo u_logo(.h(h),.y(v[9:{scale.bit_length()-1}]),.rgb(logo_rgb));
wire active={hor(0,640//scale)} && ((v >= 10'd{vstart}) && (v < 10'd{vstart+480}));
always @(posedge clk) begin
  if(h == {hw}'d{hend}) begin
    h <= {hw}'d{hstart};
    v <= (v == 10'd{vlast}) ? 10'd{vstart} : v+10'd1;
  end else h <= h-{hw}'d1;
  hsync <= !{hor(656//scale,752//scale)};
  vsync <= !((v >= 10'd{vstart+490}) && (v < 10'd{vstart+492}));
  {{r,g,b}} <= active ? logo_rgb : 3'b000;
end
endmodule
`default_nettype wire
'''
    (d/'ishi_vga_core.v').write_text(core)
    logo=np.zeros((432//scale,512//scale),dtype=np.uint8)
    for c,x0,y0,x1,y1 in rects:logo[y0:y1,x0:x1]=PALETTE[c]
    # White, including the logo's unpainted background.
    logo[logo==0]=7
    screen=np.full((480,640//scale),7,dtype=np.uint8)
    screen[24:456,64//scale:576//scale]=np.repeat(logo,scale,axis=0)
    frame=np.zeros((525,ht),dtype=np.uint8);frame[:480,:640//scale]=screen
    frame[:,:656//scale]|=8;frame[:,752//scale:]|=8
    frame[:490,:]|=16;frame[492:,:]|=16
    (d/'tests/expected_frame.hex').write_text(''.join(f'{v:02x}\n' for v in frame.flat))
    rgb=np.stack([((screen>>i)&1)*255 for i in (2,1,0)],axis=-1)
    Image.fromarray(np.repeat(rgb,scale,axis=1)).save(d/'build/reference.png')
    (d/'tests/tb_rtl.v').write_text(tb(settings,"dut.h=0; dut.v=0;"))
    cfg=(ROOT/'experiments/a_h63_v500_x/config.py').read_text()
    cfg=re.sub(r'PAD_MAP = \{.*?\n\}', 'PAD_MAP = {}', cfg, flags=re.S)
    values={'SYN_TB_RTL':repr([str(d/'tests/tb_rtl.v')]),'SYN_TB_NET':'[]',
            'BUFTH_NETS':"['clk']",'STA_FALSE_PATH_FROM':'[]',
            'STA_PERIOD_NS':str(155.0*scale/4),'N_ROWS':'4','PAD_WEIGHT':'0.0',
            'CH_HEIGHTS':'[140.4] + [151.2] * 3 + [162.0]',
            'ROUTE_CH_HEIGHTS':'[216.0] + [900.0] * 3 + [216.0]'}
    for k,v in values.items():
        cfg,n=re.subn('^'+k+r' = .*$',k+' = '+v,cfg,flags=re.M);assert n==1,k
    cfg=cfg.replace('finalize(globals())',f'HALF_SLOT = {settings!r}\nfinalize(globals())')
    (d/'config.py').write_text(cfg)
    paths=[Path(__file__),source,ROOT/'toolchain.lock.json',*[d/x for x in ['config.py','trial.json','rectangles.json','ishi_vga_core.v','ishi_logo.v','tests/expected_frame.hex','tests/tb_rtl.v']]]
    (d/'source_manifest.json').write_text(json.dumps({'scope':'unadopted seven-pad half-slot trial','sha256':{str(p.relative_to(ROOT)):sha(p) for p in paths}},indent=2)+'\n')
    print(name)


def verify(name):
    d=ROOT/'experiments'/name;settings=json.loads((d/'trial.json').read_text())
    net=d/'out/ishi_vga_core_pnr.v'
    flops=re.findall(r'^\s*(DFF|DFFRB|DFFS|MUXDFFRB)\s+(\w+)\s*\(',net.read_text(),re.M)
    assert flops and all(t=='DFF' for t,n in flops), flops
    (d/'tests/tb_gates.v').write_text(tb(settings,'\n  '.join(f'dut.{n}.q=0;' for t,n in flops)))
    exe=d/'build/postbuf.vvp'
    subprocess.run([str(ROOT/'.tools/bin/iverilog'),'-g2012','-s','tb_vga','-o',str(exe),str(d/'tests/tb_gates.v'),str(net),str(d/'build/tr1um_cells.v')],check=True,cwd=d)
    log=subprocess.check_output([str(ROOT/'.tools/bin/vvp'),str(exe)],text=True,cwd=d)
    assert 'PASS:' in log and 'FAIL' not in log
    (d/'build/postbuf.log').write_text(log)
    (d/'build/verification.json').write_text(json.dumps({'result':'PASS','scope':'final BUFTH-inserted gate model, all FF initialized to 0 by test fixture; acquisition + 2 frames',
        'limitations':'unit-delay model, no analog startup, DRC, LVS or routed timing; not exhaustive initial-state simulation',
        'sha256':{str(p.relative_to(ROOT)):sha(p) for p in [net,d/'tests/tb_gates.v',d/'tests/expected_frame.hex',d/'build/tr1um_cells.v']}},indent=2)+'\n')
    print(name,log)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['generate','verify']);ap.add_argument('value');ap.add_argument('--scale',type=int,default=4)
    a=ap.parse_args()
    if a.action=='generate':generate(a.value,a.scale)
    else:verify(a.value)
