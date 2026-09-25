`timescale 1ns/1ps
module tb_vga;
reg clk=0;
wire r,g,b,hsync,vsync;
ishi_vga_core dut(.clk(clk),.r(r),.g(g),.b(b),.hsync(hsync),.vsync(vsync));
real half_period=158.730158730159;
initial begin
  if ($value$plusargs("HALF_NS=%f",half_period)) begin end
  forever #(half_period) clk=~clk;
end
reg [4:0] expected[0:52499];
integer i,idx,fd,tries;
reg prev_vs;
initial begin
  // Test fixture only: the ASIC has NO initialized state or reset port.
  dut.h=0; dut.v=0;
  $readmemh("tests/expected_frame.hex",expected);
  repeat (105000) begin @(posedge clk); #35; end
  prev_vs=vsync;
  tries=0;
  begin : seek
    forever begin
      @(posedge clk); #35;
      tries=tries+1;
      if (prev_vs===1'b1 && vsync===1'b0) disable seek;
      if (tries>52500) $fatal(1,"FAIL: no VSYNC after startup");
      prev_vs=vsync;
    end
  end
  idx=49000;
  fd=$fopen("build/observed.hex","w");
  for(i=0;i<105000;i=i+1) begin
    if ({vsync,hsync,r,g,b} !== expected[idx])
      $fatal(1,"FAIL: tick=%0d idx=%0d got=%h expected=%h",i,idx,{vsync,hsync,r,g,b},expected[idx]);
    if(i<52500) $fdisplay(fd,"%02x",{vsync,hsync,r,g,b});
    idx=(idx+1)%52500;
    @(posedge clk); #35;
  end
  $fclose(fd);
  $display("PASS: 105000 pixel ticks, reset-free acquisition and two exact frames");
  $finish;
end
initial begin #300000000; $fatal(1,"FAIL: watchdog"); end
endmodule
