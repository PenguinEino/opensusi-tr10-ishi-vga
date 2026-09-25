`timescale 1ns/1ps
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
  g._394_.q=0;
  g._395_.q=0;
  g._396_.q=0;
  g._397_.q=0;
  g._398_.q=0;
  g._399_.q=0;
  g._400_.q=0;
  g._401_.q=0;
  g._402_.q=0;
  g._403_.q=0;
  g._404_.q=0;
  g._405_.q=0;
  g._406_.q=0;
  g._407_.q=0;
  g._408_.q=0;
  g._409_.q=0;
  g._410_.q=0;
  g._411_.q=0;
  g._412_.q=0;
  g._413_.q=0;
  g._414_.q=0;
  g._415_.q=0;
  valid=0;
  for(s=0;s<131072;s=s+1) begin
    hv=s & 127; vv=s >> 7;
    r.h=hv; r.v=vv;
  g._409_.q = hv[0];
  g._410_.q = hv[1];
  g._411_.q = hv[2];
  g._412_.q = hv[3];
  g._413_.q = hv[4];
  g._414_.q = hv[5];
  g._415_.q = hv[6];
  g._399_.q = vv[0];
  g._400_.q = vv[1];
  g._401_.q = vv[2];
  g._402_.q = vv[3];
  g._403_.q = vv[4];
  g._404_.q = vv[5];
  g._405_.q = vv[6];
  g._406_.q = vv[7];
  g._407_.q = vv[8];
  g._408_.q = vv[9];
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
