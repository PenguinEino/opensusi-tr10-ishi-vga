#!/usr/bin/env python3
"""Alternative vertical scan using exact interval lengths instead of Y comparisons."""
from pathlib import Path
import re,json
ROOT=Path(__file__).resolve().parents[1]
baseline=(ROOT/'rtl/ishi_vga_core.v').read_text()
logo=(ROOT/'rtl/ishi_logo.v').read_text()
ys=sorted({int(v)*4 for v in re.findall(r"y [<>]=? 8'd(\d+)",logo)}|{0,480,490,492,525})
lengths=[b-a for a,b in zip(ys,ys[1:])]
assert len(lengths)==20
n=len(lengths)
for encoding in ['binary','onehot']:
 d=ROOT/'experiments'/f'arch_vevents_{encoding}';d.mkdir(exist_ok=True)
 (d/'build').mkdir(exist_ok=True);(d/'tests').mkdir(exist_ok=True)
 p=d/'tests/expected_frame.hex'
 if not p.exists():p.symlink_to('../../../tests/expected_frame.hex')
 if encoding=='binary':
  decl="(* fsm_encoding = \"none\" *) reg [4:0] row_band;"
  code=lambda i:f"5'd{i}"
  cond=lambda i:f"row_band == 5'd{i}"
  l=logo.replace('input wire [7:0] y','input wire [4:0] row_band')
 else:
  decl=f"reg [{n-1}:0] row_band;"
  code=lambda i:f"{n}'d{1<<i}"
  cond=lambda i:f"row_band[{i}]"
  l=logo.replace('input wire [7:0] y',f'input wire [{n-1}:0] row_band')
 def ym(m):
  lo,hi=[int(x)*4 for x in m.groups()];ids=[i for i,y in enumerate(ys[:-1]) if lo<=y<hi]
  if encoding=='binary':return f"((row_band >= 5'd{ids[0]}) && (row_band <= 5'd{ids[-1]}))"
  return '('+' | '.join(cond(i) for i in ids)+')'
 l=re.sub(r"\(y >= 8'd(\d+)\) && \(y < 8'd(\d+)\)",ym,l)
 c=baseline.replace('reg [9:0] v;',decl+'\n    reg [6:0] remaining;')
 c=c.replace('.y(v[9:2])','.row_band(row_band)')
 c=c.replace("(v < 10'd480)",'('+' | '.join(cond(i) for i,y in enumerate(ys[:-1]) if y<480)+')')
 c=c.replace("((v >= 10'd490) && (v < 10'd492))",'('+cond(ys.index(490))+')')
 c=c.replace("v <= 10'd0;",f"row_band <= {code(0)}; remaining <= 7'd{lengths[0]-1};")
 cases='\n'.join(f"                        {code(i)}: begin remaining <= 7'd{lengths[(i+1)%n]-1}; row_band <= {code((i+1)%n)}; end" for i in range(n))
 nxt="if (remaining != 0) remaining <= remaining - 1'b1;\n                else begin\n                    case (row_band)\n"+cases+f"\n                        default: begin remaining <= 7'd{lengths[0]-1}; row_band <= {code(0)}; end\n                    endcase\n                end"
 c=c.replace("v <= (v == 10'd524) ? 10'd0 : v + 10'd1;",nxt)
 (d/'ishi_vga_core.v').write_text(c);(d/'ishi_logo.v').write_text(l)
 cfg=(ROOT/'config.py').read_text().replace("SYN_RTL = ['rtl/ishi_vga_core.v', 'rtl/ishi_logo.v']","SYN_RTL = ['ishi_vga_core.v', 'ishi_logo.v']").replace("['tests/tb_vga.v']",repr([str(ROOT/'tests/tb_vga.v')]))
 (d/'config.py').write_text(cfg)
 (d/'intervals.json').write_text(json.dumps({'boundaries':ys,'lengths':lengths},indent=2)+'\n')
print(ys,lengths)
