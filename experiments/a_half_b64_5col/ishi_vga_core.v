`timescale 1ns/1ps
`default_nettype none
// Reset-free trial. No FPGA power-on initialization is synthesized.
module ishi_vga_core(input wire clk, output reg r,g,b,hsync,vsync);
reg [6:0] h;
reg [9:0] v;
wire [2:0] logo_rgb;
ishi_logo u_logo(.h(h),.y(v[9:3]),.rgb(logo_rgb));
wire active=((h >= 7'd80) | (h < 7'd32)) && ((v >= 10'd488) && (v < 10'd968));
always @(posedge clk) begin
  if(h == 7'd60) begin
    h <= 7'd31;
    v <= (v == 10'd1012) ? 10'd488 : v+10'd1;
  end else h <= h-7'd1;
  hsync <= !((h >= 7'd66) && (h < 7'd78));
  vsync <= !((v >= 10'd978) && (v < 10'd980));
  {r,g,b} <= active ? logo_rgb : 3'b000;
end
endmodule
`default_nettype wire
