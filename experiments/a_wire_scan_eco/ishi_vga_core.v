`timescale 1ns/1ps
`default_nettype none
module ishi_vga_core(input wire clk,output reg r,g,b,hsync,vsync);
reg [6:0] h;
reg [9:0] v;
wire [2:0] logo_rgb;
ishi_logo u_logo(.h(h),.v(v),.rgb(logo_rgb));
reg [5:0] phase;
wire on = logo_rgb[1] & ((~h[5:3]) == phase[5:3]);
wire [2:0] animated_rgb = {logo_rgb[2] | on, logo_rgb[1:0]};
always @(posedge clk) begin
  if ((h == 7'd100) && (v == 10'd0)) phase <= phase + 6'd1;
  if(h==7'd100) begin
    h<=7'd71;
    v<=(v==10'd0) ? 10'd500 : v+10'd1;
  end else h<=h-7'd1;
  hsync<=!((h>=7'd106)&&(h<7'd118));
  vsync<=!((v>=10'd990)&&(v<10'd992));
  {r,g,b}<=animated_rgb;
end
endmodule
`default_nettype wire
