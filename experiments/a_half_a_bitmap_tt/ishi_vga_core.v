`timescale 1ns/1ps
`default_nettype none
// Reset-free trial. No FPGA power-on initialization is synthesized.
module ishi_vga_core(input wire clk, output reg r,g,b,hsync,vsync);
reg [7:0] h;
reg [9:0] v;
wire [2:0] logo_rgb;
ishi_logo u_logo(.h(h[6:0]),.y(v[8:2]),.rgb(logo_rgb));
always @(posedge clk) begin
  if(h == 8'd200) begin
    h <= 8'd143;
    v <= (v == 10'd0) ? 10'd500 : v+10'd1;
  end else h <= h-8'd1;
  hsync <= !((h >= 8'd212) && (h < 8'd236));
  vsync <= !((v >= 10'd990) && (v < 10'd992));
  {r,g,b} <= h[7] ? 3'b000 : logo_rgb;
end
endmodule
`default_nettype wire
