`timescale 1ns/1ps
`default_nettype none
// 6.30 MHz: 31.5 kHz horizontal, 60 Hz vertical. One tick = four VGA pixels.
// Ring oscillator belongs to the physical chip wrapper, never to this RTL.
module ishi_vga_core (
    input wire clk,
    input wire reset_n,
    output wire [1:0] r,
    output wire [1:0] g,
    output wire [1:0] b,
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

    // The six logo colors plus blank are uniquely identified by R1,G1,G0.
    // These 3 physical output bits stay registered. The other 3 use shallow
    // combinational decoding; their output delay/glitches need assessment.
    reg r_high, g_high, g_low;
    assign r = {r_high, g_low | (~r_high & g_high)};
    assign g = {g_high, g_low};
    assign b = {g_high | (~r_high & g_low), r_high | g_high | g_low};
    reg [7:0] h;
    reg [9:0] v;
    wire [5:0] logo_rgb;
    ishi_logo u_logo (.h(h), .y(v[9:2]), .rgb(logo_rgb));
    wire active = (h < 8'd160) && (v < 10'd480);

    // RGB and sync all refer to the same pre-edge counter values.
    always @(posedge clk or negedge running) begin
        if (!running) begin
            h <= 8'd0;
            v <= 10'd0;
            r_high <= 0; g_high <= 0; g_low <= 0;
            hsync <= 1'b1;
            vsync <= 1'b1;
        end else begin
            if (h == 8'd199) begin
                h <= 8'd0;
                v <= (v == 10'd524) ? 10'd0 : v + 10'd1;
            end else h <= h + 8'd1;
            hsync <= !((h >= 8'd164) && (h < 8'd188));
            vsync <= !((v >= 10'd490) && (v < 10'd492));
            {r_high,g_high,g_low} <= active ? {logo_rgb[5],logo_rgb[3:2]} : 3'd0;
        end
    end
endmodule
`default_nettype wire
