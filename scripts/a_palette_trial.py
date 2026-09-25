#!/usr/bin/env python3
"""Feasibility trial: exact A colors over three registered palette-code pins.

External combinational palette decoder is in the testbench, never silently
included in the chip area. This is an alternative interface, not adopted RTL.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'experiments/a_h63_v500_x'
DST=ROOT/'experiments/a_palette3'


def main():
    assert not DST.exists()
    for sub in ('build','tests'):(DST/sub).mkdir(parents=True,exist_ok=True)
    core=(SRC/'ishi_vga_core.v').read_text()
    original='    output reg [1:0] r,\n    output reg [1:0] g,\n    output reg [1:0] b,'
    assert original in core
    core=core.replace(original,'    output reg [2:0] pixel,')
    old="            r <= 2'd0;\n            g <= 2'd0;\n            b <= 2'd0;"
    assert old in core
    core=core.replace(old,"            pixel <= 3'd0;")
    old="{r,g,b} <= active ? logo_rgb : 6'b000000;"
    assert old in core
    core=core.replace(old,"pixel <= active ? {logo_rgb[5], logo_rgb[3:2]} : 3'b000;")
    (DST/'ishi_vga_core.v').write_text('// Feasibility only: external palette decoder required.\n'+core)
    (DST/'ishi_logo.v').write_bytes((SRC/'ishi_logo.v').read_bytes())
    (DST/'tests/expected_frame.hex').write_bytes((SRC/'tests/expected_frame.hex').read_bytes())
    tb=(ROOT/'tests/tb_vga.v').read_text()
    old='    wire [1:0] r,g,b;'
    assert old in tb
    tb=tb.replace(old,'''    wire [1:0] r,g,b;
    wire [2:0] pixel;
    // External decoder, NOT part of the synthesized ASIC.
    wire a=pixel[2], bb=pixel[1], c=pixel[0];
    assign r={a, c | (~a & bb)};
    assign g={bb,c};
    assign b={bb | (~a & c), a | bb | c};''')
    tb=tb.replace('.r(r),.g(g),.b(b)', '.pixel(pixel)')
    (DST/'tests/tb_palette.v').write_text(tb)
    cfg=(SRC/'config.py').read_text()
    for key in ['SYN_TB_RTL','SYN_TB_NET']:
        cfg,n=re.subn('^'+key+r' = .*$',key+' = '+repr([str(DST/'tests/tb_palette.v')]),cfg,flags=re.M)
        assert n==1
    cfg=cfg.replace('finalize(globals())', '''# Feasibility alternative: no pad/frame integration authorized here.
PALETTE_INTERFACE = {'bits': 3, 'external_decode': True, 'adopted': False}
PAD_MAP = {}
PAD_WEIGHT = 0.0
finalize(globals())''')
    (DST/'config.py').write_text(cfg)
    paths=[Path(__file__),ROOT/'toolchain.lock.json',ROOT/'tests/tb_vga.v',SRC/'ishi_vga_core.v',SRC/'ishi_logo.v',
           DST/'config.py',DST/'ishi_vga_core.v',DST/'ishi_logo.v',DST/'tests/tb_palette.v',DST/'tests/expected_frame.hex']
    (DST/'source_manifest.json').write_text(json.dumps({'scope':'unadopted 3-bit external palette interface',
        'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},indent=2)+'\n')
    print(DST)


if __name__=='__main__':main()
