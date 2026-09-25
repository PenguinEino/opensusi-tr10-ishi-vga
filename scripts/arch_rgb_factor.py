#!/usr/bin/env python3
"""Encode the seven reachable RGB222 colors using actual registered RGB bits."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
core=(ROOT/'rtl/ishi_vga_core.v').read_text()
logo=(ROOT/'rtl/ishi_logo.v').read_text()
for variant in ['rgb5','rgb3']:
 d=ROOT/'experiments'/('arch_'+variant);d.mkdir(exist_ok=True)
 (d/'build').mkdir(exist_ok=True);(d/'tests').mkdir(exist_ok=True)
 p=d/'tests/expected_frame.hex'
 if not p.exists():p.symlink_to('../../../tests/expected_frame.hex')
 c=core
 if variant=='rgb5':
  c=c.replace('output reg [1:0] b','output wire [1:0] b')
  c=c.replace('    reg [7:0] h;',"    reg b_high;\n    assign b = {b_high, r[0] | r[1]};\n    reg [7:0] h;")
  c=c.replace("b <= 2'd0;","b_high <= 1'b0;")
  c=c.replace("{r,g,b} <= active ? logo_rgb : 6'b000000;","{r,g,b_high} <= active ? logo_rgb[5:1] : 5'b00000;")
 else:
  c=c.replace('output reg [1:0]','output wire [1:0]')
  c=c.replace('    reg [7:0] h;',"""    // The six logo colors plus blank are uniquely identified by R1,G1,G0.
    // These 3 physical output bits stay registered. The other 3 use shallow
    // combinational decoding; their output delay/glitches need assessment.
    reg r_high, g_high, g_low;
    assign r = {r_high, g_low | (~r_high & g_high)};
    assign g = {g_high, g_low};
    assign b = {g_high | (~r_high & g_low), r_high | g_high | g_low};
    reg [7:0] h;""")
  c=c.replace("r <= 2'd0;\n            g <= 2'd0;\n            b <= 2'd0;","r_high <= 0; g_high <= 0; g_low <= 0;")
  c=c.replace("{r,g,b} <= active ? logo_rgb : 6'b000000;","{r_high,g_high,g_low} <= active ? {logo_rgb[5],logo_rgb[3:2]} : 3'd0;")
 (d/'ishi_vga_core.v').write_text(c);(d/'ishi_logo.v').write_text(logo)
 cfg=(ROOT/'config.py').read_text().replace("SYN_RTL = ['rtl/ishi_vga_core.v', 'rtl/ishi_logo.v']","SYN_RTL = ['ishi_vga_core.v', 'ishi_logo.v']").replace("['tests/tb_vga.v']",repr([str(ROOT/'tests/tb_vga.v')]))
 (d/'config.py').write_text(cfg)
