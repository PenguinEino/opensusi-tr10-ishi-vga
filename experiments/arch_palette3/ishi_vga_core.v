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

    reg [7:0] h;
    reg [9:0] v;
    wire [2:0] logo_code;
    reg [2:0] color_code;
    reg [5:0] rgb_decoded;
    assign {r,g,b} = rgb_decoded;
    always @* begin
        case (color_code)
            3'd0: rgb_decoded = 6'd0;
            3'd1: rgb_decoded = 6'd63;
            3'd2: rgb_decoded = 6'd27;
            3'd3: rgb_decoded = 6'd53;
            3'd4: rgb_decoded = 6'd31;
            3'd5: rgb_decoded = 6'd23;
            3'd6: rgb_decoded = 6'd43;
            default: rgb_decoded = 6'd0;
        endcase
    end
    ishi_logo u_logo (.h(h), .y(v[9:2]), .code(logo_code));
    wire active = (h < 8'd160) && (v < 10'd480);

    // RGB and sync all refer to the same pre-edge counter values.
    always @(posedge clk or negedge running) begin
        if (!running) begin
            h <= 8'd0;
            v <= 10'd0;
            color_code <= 3'd0;
            hsync <= 1'b1;
            vsync <= 1'b1;
        end else begin
            if (h == 8'd199) begin
                h <= 8'd0;
                v <= (v == 10'd524) ? 10'd0 : v + 10'd1;
            end else h <= h + 8'd1;
            hsync <= !((h >= 8'd164) && (h < 8'd188));
            vsync <= !((v >= 10'd490) && (v < 10'd492));
            color_code <= active ? logo_code : 3'd0;
        end
    end
endmodule
`default_nettype wire
