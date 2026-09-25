`timescale 1ns/1ps
`default_nettype none
module ishi_vga_core(input wire clk,output reg r,g,b,hsync,vsync);
reg [6:0] h;
reg [9:0] v;
wire [2:0] logo_rgb;
ishi_logo u_logo(.h(h),.v(v),.rgb(logo_rgb));
reg [5:0] phase;
wire [2:0] animated_rgb = phase[5] ? {logo_rgb[1],logo_rgb[2],logo_rgb[0]} : logo_rgb;
always @(posedge clk) begin
  phase <= phase + {5'b0, ((h == 7'd100) && (v == 10'd0))};
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
