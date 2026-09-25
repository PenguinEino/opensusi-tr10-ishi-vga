from pathlib import Path
import re
import json

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
src=ROOT/'submission/source'
net=(src/'ishi_vga_core_pnr.v').read_text()
(OUT/'gates_renamed.v').write_text(net.replace('module ishi_vga_core(', 'module gate_core(', 1))
dffs={}
for inst,body in re.findall(r'DFF\s+(\w+)\s*\((.*?)\);',net,re.S):
    pins=dict(re.findall(r'\.(\w+)\(([^)]+)\)',body))
    dffs[pins['Q']]=inst
assert len(dffs)==22
state_sets='\n'.join(f'  g.{dffs[f"{a}[{i}]"]}.q = {v}[{i}];' for a,n,v in [('h',7,'hv'),('v',10,'vv')] for i in range(n))
init='\n'.join(f'  g.{inst}.q=0;' for inst in dffs.values())
tb='''`timescale 1ns/1ps
module tb_exhaustive;
reg clk=0;
wire rr,rg,rb,rhs,rvs,gr,gg,gb,ghs,gvs;
ishi_vga_core r(.clk(clk),.r(rr),.g(rg),.b(rb),.hsync(rhs),.vsync(rvs));
gate_core g(.clk(clk),.r(gr),.g(gg),.b(gb),.hsync(ghs),.vsync(gvs));
reg [4:0] expected [0:52499];
reg [6:0] hv,nh;
reg [9:0] vv,nv;
integer s,x,y,valid;
initial begin
  $readmemh("../../submission/tests/expected_frame.hex",expected);
INIT
  valid=0;
  for(s=0;s<131072;s=s+1) begin
    hv=s & 127; vv=s >> 7;
    r.h=hv; r.v=vv;
SETS
    #80; clk=1; #80;
    nh=(hv==100) ? 71 : hv-7'd1;
    nv=(hv==100) ? ((vv==0) ? 500 : vv+10'd1) : vv;
    if (r.h !== nh || r.v !== nv || g.h !== nh || g.v !== nv)
      $fatal(1,"FAIL: state=%0d transition RTL=%0d,%0d gates=%0d,%0d expected=%0d,%0d",s,r.h,r.v,g.h,g.v,nh,nv);
    if ({rvs,rhs,rr,rg,rb} !== {gvs,ghs,gr,gg,gb})
      $fatal(1,"FAIL: state=%0d outputs differ",s);
    x=(71-hv+128)%128; y=(vv-500+1024)%1024;
    if(x<100 && y<525) begin
      valid=valid+1;
      if ({rvs,rhs,rr,rg,rb} !== expected[y*100+x])
        $fatal(1,"FAIL: frame state=%0d",s);
    end
    clk=0; #80;
  end
  if(valid != 52500) $fatal(1,"wrong raster state count");
  $display("PASS: all 131072 binary counter states; RTL/gates next-state and 5 outputs; 52500 raster reference states");
  $finish;
end
endmodule
'''.replace('INIT',init).replace('SETS',state_sets)
(OUT/'tb_exhaustive.v').write_text(tb)
(OUT/'out').mkdir(exist_ok=True)
(OUT/'out/ishi_vga_core_pnr.v').write_text(net)
report='''puts "=== Additional electrical checks: ideal clock ==="
check_setup -verbose
report_check_types -max_capacitance -max_slew -violators -digits 6
report_net clk_buf
puts "=== Cell-propagated clock, no interconnect RC ==="
set_propagated_clock [all_clocks]
set_input_transition 1.2 [get_ports clk]
report_check_types -max_capacitance -max_slew -violators -digits 6
report_checks -path_delay min_max -format full_clock_expanded -fields {slew cap fanout} -digits 6 -group_path_count 2
report_clock_min_period
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -format full_clock_expanded -fields {slew cap fanout} -digits 6
'''
(OUT/'electrical.tcl').write_text(report)
print(json.dumps({'clock_ff_count':len(dffs),'counter_states':131072,'scratch':str(OUT)},indent=2))
