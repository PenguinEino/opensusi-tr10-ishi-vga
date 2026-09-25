`timescale 1ns/1ps
module tb;
reg clk=0;
always #158.730158730159 clk=~clk;
wire [4:0] observed,rtl_observed;
rtl_core rtl(.clk(clk),.vsync(rtl_observed[4]),.hsync(rtl_observed[3]),.r(rtl_observed[2]),.g(rtl_observed[1]),.b(rtl_observed[0]));
ishi_vga_core dut(.clk(clk),.vsync(observed[4]),.hsync(observed[3]),.r(observed[2]),.g(observed[1]),.b(observed[0]));
reg [4:0] reference [0:52499];
reg [4:0] expected;
integer frame,tick,x,fd,seed,next_phase;
initial begin
 dut._394_.q=1'b0;
dut._395_.q=1'b0;
dut._396_.q=1'b0;
dut._397_.q=1'b0;
dut._398_.q=1'b0;
dut._399_.q=1'b0;
dut._400_.q=1'b0;
dut._401_.q=1'b1;
dut._402_.q=1'b0;
dut._403_.q=1'b1;
dut._404_.q=1'b1;
dut._405_.q=1'b1;
dut._406_.q=1'b1;
dut._407_.q=1'b1;
dut._408_.q=1'b0;
dut._409_.q=1'b1;
dut._410_.q=1'b1;
dut._411_.q=1'b1;
dut._412_.q=1'b0;
dut._413_.q=1'b0;
dut._414_.q=1'b0;
dut._415_.q=1'b1;
dut.anim_44_.q=1'b0;
dut.anim_45_.q=1'b0;
dut.anim_46_.q=1'b0;
dut.anim_47_.q=1'b0;
dut.anim_48_.q=1'b0;
dut.anim_49_.q=1'b0;
dut.anim_50_.q=1'b0;
 rtl.h=71;rtl.v=500;rtl.phase=0;rtl.r=0;rtl.g=0;rtl.b=0;rtl.hsync=0;rtl.vsync=0;
 $readmemh("/home/ishi-kai/ishi-vga/designs/grid_power/tests/expected_frame.hex",reference);
 fd=$fopen("observed.bin","wb");
 for(frame=0;frame<128;frame=frame+1) begin
  for(tick=0;tick<52500;tick=tick+1) begin
   @(posedge clk);#80;
   x=tick%100;expected=reference[tick];
   if(expected[2:0]==4 && frame<64 && x>=8 && x<72 && ((x-8)/16)==frame/16) expected[2:0]=7;
   if(observed !== expected || rtl_observed !== expected) $fatal(1,"frame=%0d tick=%0d got=%h expected=%h",frame,tick,observed,expected);
   if((frame%16)==0 && frame<=64) $fwrite(fd,"%c",observed);
   @(negedge clk);#1;
  end
  if({dut.anim_phase_6_,dut.anim_phase_5_,dut.anim_phase_4_,dut.anim_phase_3_,dut.anim_phase_2_,dut.anim_phase_1_,dut.anim_phase_0_} !== ((frame+1)%128))
   $fatal(1,"phase transition at frame %0d",frame);
 end
 $fclose(fd);
 for(seed=0;seed<128;seed=seed+1) begin
  dut._394_.q=1'b0;
dut._395_.q=1'b0;
dut._396_.q=1'b0;
dut._397_.q=1'b0;
dut._398_.q=1'b0;
dut._399_.q=1'b0;
dut._400_.q=1'b0;
dut._401_.q=1'b0;
dut._402_.q=1'b0;
dut._403_.q=1'b0;
dut._404_.q=1'b0;
dut._405_.q=1'b0;
dut._406_.q=1'b0;
dut._407_.q=1'b0;
dut._408_.q=1'b0;
dut._409_.q=1'b0;
dut._410_.q=1'b0;
dut._411_.q=1'b1;
dut._412_.q=1'b0;
dut._413_.q=1'b0;
dut._414_.q=1'b1;
dut._415_.q=1'b1;
dut.anim_44_.q=seed[4];
dut.anim_45_.q=seed[5];
dut.anim_46_.q=seed[6];
dut.anim_47_.q=seed[0];
dut.anim_48_.q=seed[1];
dut.anim_49_.q=seed[2];
dut.anim_50_.q=seed[3];
  rtl.h=100;rtl.v=0;rtl.phase=seed;
  next_phase=(seed+1)%128;
  @(posedge clk);#80;
  if({dut.anim_phase_6_,dut.anim_phase_5_,dut.anim_phase_4_,dut.anim_phase_3_,dut.anim_phase_2_,dut.anim_phase_1_,dut.anim_phase_0_} !== next_phase || rtl.phase !== next_phase)
   $fatal(1,"initial phase state %0d",seed);
  @(negedge clk);#1;
 end
 $display("PASS: 128 continuous RTL/gate frames, 6720000 RGB/HS/VS ticks, all 128 phase transitions, all 128 binary phase initial states; stage lengths 16/16/16/16/64 frames");
 $finish;
end
initial begin #2300000000;$fatal(1,"watchdog");end
endmodule
