#!/usr/bin/env python3
"""Generate reproducible isolated B-image timing/core architecture experiments."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
base_config=(ROOT/'config.py').read_text()
base_core=(ROOT/'rtl/ishi_vga_core.v').read_text()
base_logo=(ROOT/'rtl/ishi_logo.v').read_text()

def write(name,core,logo=base_logo):
 d=ROOT/'experiments'/('arch_'+name);d.mkdir(parents=True,exist_ok=True)
 (d/'build').mkdir(exist_ok=True)
 (d/'tests').mkdir(exist_ok=True)
 expected=d/'tests/expected_frame.hex'
 if not expected.exists(): expected.symlink_to('../../../tests/expected_frame.hex')
 (d/'ishi_vga_core.v').write_text(core)
 (d/'ishi_logo.v').write_text(logo)
 c=base_config.replace("SYN_RTL = ['rtl/ishi_vga_core.v', 'rtl/ishi_logo.v']","SYN_RTL = ['ishi_vga_core.v', 'ishi_logo.v']")
 c=c.replace("['tests/tb_vga.v']",repr([str(ROOT/'tests/tb_vga.v')]))
 c=c.replace('finalize(globals())', '''# Fresh namespace from config_base, all design values assigned before finalization.
finalize(globals())''')
 (d/'config.py').write_text(c)

write('base',base_core)
# Use synchronous reset for counter state; synchronizer's two edges initialize
# counters before visible output resumes, even after a stopped-clock reset.
pos=base_core.index('    // RGB and sync')
sync=base_core[:pos]+'''    always @(posedge clk) begin
        if (!running) begin h <= 0; v <= 0; end
        else if (h == 8'd199) begin
            h <= 0;
            v <= (v == 10'd524) ? 0 : v + 1'b1;
        end else h <= h + 1'b1;
    end
'''+base_core[pos:]
sync=sync.replace("            h <= 8'd0;\n            v <= 10'd0;\n",'')
sync=sync.replace("            if (h == 8'd199) begin\n                h <= 8'd0;\n                v <= (v == 10'd524) ? 10'd0 : v + 10'd1;\n            end else h <= h + 8'd1;\n",'')
write('sync_counters',sync)
# Replace 6 RGB FFs with a registered 3-bit color code, then a small decode.
palette=[0,63,27,53,31,23,43]
logo=base_logo.replace('output reg [5:0] rgb','output reg [2:0] code')
for code,rgb in enumerate(palette): logo=logo.replace("rgb = 6'b"+format(rgb,'06b'),"code = 3'd"+str(code))
core=base_core.replace('output reg [1:0]','output wire [1:0]')
core=core.replace('wire [5:0] logo_rgb;','wire [2:0] logo_code;\n    reg [2:0] color_code;\n    reg [5:0] rgb_decoded;\n    assign {r,g,b} = rgb_decoded;\n    always @* begin\n        case (color_code)\n'+''.join(f"            3'd{i}: rgb_decoded = 6'd{rgb};\n" for i,rgb in enumerate(palette))+"            default: rgb_decoded = 6'd0;\n        endcase\n    end")
core=core.replace('.rgb(logo_rgb)','.code(logo_code)')
core=core.replace("            r <= 2'd0;\n            g <= 2'd0;\n            b <= 2'd0;","            color_code <= 3'd0;")
core=core.replace("{r,g,b} <= active ? logo_rgb : 6'b000000;","color_code <= active ? logo_code : 3'd0;")
write('palette3',core,logo)
# Separate low-order phase counters from their high bits. Timing stays exact.
split=base_core.replace('reg [7:0] h;','reg [2:0] hx;\n    reg [4:0] hb;\n    wire [7:0] h = {hb,hx};')
split=split.replace('reg [9:0] v;','reg [1:0] vy;\n    reg [7:0] vb;\n    wire [9:0] v = {vb,vy};')
split=split.replace("h <= 8'd0;","hx <= 0; hb <= 0;").replace("v <= 10'd0;","vy <= 0; vb <= 0;")
split=split.replace("v <= (v == 10'd524) ? 10'd0 : v + 10'd1;","if (v == 10'd524) begin vy <= 0; vb <= 0; end\n                else begin vy <= vy + 1'b1; if (&vy) vb <= vb + 1'b1; end")
split=split.replace("end else h <= h + 8'd1;","end else begin hx <= hx + 1'b1; if (&hx) hb <= hb + 1'b1; end")
write('split_counters',split)
# Offset horizontal counter to put terminal condition on all ones and translate
# rectangle bounds, preserving combinational comparisons and external phase.
for off in [16,56,96]:
 c=base_core.replace("h <= 8'd0;",f"h <= 8'd{off};").replace("h == 8'd199",f"h == 8'd{(199+off)%256}")
 # For offsets whose active interval wraps, retain expression to original h.
 if off<=56:
  c=c.replace("h < 8'd160",f"h < 8'd{160+off}")
  c=c.replace("h >= 8'd164",f"h >= 8'd{164+off}").replace("h < 8'd188",f"h < 8'd{188+off}")
  l=re.sub(r"h (>=|<) 8'd(\d+)",lambda m:f"h {m[1]} 8'd{int(m[2])+off}",base_logo)
 else:
  continue
 write('hoffset'+str(off),c,l)
print('generated arch_* core variants')

def interval(signal,a,b,offset,width):
 n=1<<width;a=(a+offset)%n;b=(b+offset)%n
 if a<b:
  return f"(({signal} >= {width}'d{a}) && ({signal} < {width}'d{b}))"
 if b==0: return f"({signal} >= {width}'d{a})"
 return f"(({signal} >= {width}'d{a}) || ({signal} < {width}'d{b}))"

def offset_core(h_offset,v_offset):
 c=base_core.replace("h <= 8'd0;",f"h <= 8'd{h_offset%256};").replace("h == 8'd199",f"h == 8'd{(199+h_offset)%256}")
 c=c.replace("v <= 10'd0;",f"v <= 10'd{v_offset%1024};").replace("v == 10'd524",f"v == 10'd{(524+v_offset)%1024}").replace("? 10'd0 :",f"? 10'd{v_offset%1024} :")
 c=c.replace("(h < 8'd160)",interval('h',0,160,h_offset,8)).replace("(v < 10'd480)",interval('v',0,480,v_offset,10))
 c=c.replace("((h >= 8'd164) && (h < 8'd188))",interval('h',164,188,h_offset,8))
 c=c.replace("((v >= 10'd490) && (v < 10'd492))",interval('v',490,492,v_offset,10))
 l=base_logo
 for signal,off in [('h',h_offset),('y',v_offset//4)]:
  pat=rf"\({signal} >= 8'd(\d+)\) && \({signal} < 8'd(\d+)\)"
  l=re.sub(pat,lambda m:interval(signal,int(m[1]),int(m[2]),off,8),l)
 return c,l
for ho in [-56,-48,-40,-32,-24,-16,-8,8,24,32,40,48,64,80]:
 write(f'offset_h{ho}'.replace('-','m'),*offset_core(ho,0))
for vo in [-128,-96,-76,-64,-32,32,64,128,256,500]:
 write(f'offset_v{vo}'.replace('-','m'),*offset_core(0,vo))
