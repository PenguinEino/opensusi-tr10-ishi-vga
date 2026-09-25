`timescale 1ns/1ps
`default_nettype none
// 6.30 MHz: 31.5 kHz horizontal, 60 Hz vertical. One tick = four VGA pixels.
// Ring oscillator belongs to the physical chip wrapper, never to this RTL.
module ishi_vga_core (
    input wire clk,
    input wire reset_n,
    output reg [1:0] r,
    output reg [1:0] g,
    output reg [1:0] b,
    output reg hsync,
    output reg vsync
);
    // Asynchronous assertion works even when the external clock is stopped.
    // Two clocks synchronize release; the core starts on the following edge.
    (* async_reg = "true" *) reg [1:0] reset_pipe;
    always @(posedge clk or negedge reset_n)
        if (!reset_n) reset_pipe <= 2'b00;
        else reset_pipe <= {reset_pipe[0], 1'b1};
    wire running = reset_pipe[1];

    reg [7:0] h;
    reg [9:0] v;
    wire [5:0] logo_rgb;
    ishi_logo u_logo (.h(h), .y(v[9:2]), .rgb(logo_rgb));
    wire active = ((h >= 8'd200) || (h < 8'd104)) && ((v >= 10'd0) && (v < 10'd480));

    // RGB and sync all refer to the same pre-edge counter values.
    always @(posedge clk or negedge running) begin
        if (!running) begin
            h <= 8'd200;
            v <= 10'd0;
            r <= 2'd0;
            g <= 2'd0;
            b <= 2'd0;
            hsync <= 1'b1;
            vsync <= 1'b1;
        end else begin
            if (h == 8'd143) begin
                h <= 8'd200;
                v <= (v == 10'd524) ? 10'd0 : v + 10'd1;
            end else h <= h + 8'd1;
            hsync <= !((h >= 8'd108) && (h < 8'd132));
            vsync <= !((v >= 10'd490) && (v < 10'd492));
            {r,g,b} <= active ? logo_rgb : 6'b000000;
        end
    end
endmodule
`default_nettype wire
