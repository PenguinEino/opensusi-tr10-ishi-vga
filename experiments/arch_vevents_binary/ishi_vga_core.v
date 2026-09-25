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
    (* fsm_encoding = "none" *) reg [4:0] row_band;
    reg [6:0] remaining;
    wire [5:0] logo_rgb;
    ishi_logo u_logo (.h(h), .row_band(row_band), .rgb(logo_rgb));
    wire active = (h < 8'd160) && (row_band == 5'd0 | row_band == 5'd1 | row_band == 5'd2 | row_band == 5'd3 | row_band == 5'd4 | row_band == 5'd5 | row_band == 5'd6 | row_band == 5'd7 | row_band == 5'd8 | row_band == 5'd9 | row_band == 5'd10 | row_band == 5'd11 | row_band == 5'd12 | row_band == 5'd13 | row_band == 5'd14 | row_band == 5'd15 | row_band == 5'd16);

    // RGB and sync all refer to the same pre-edge counter values.
    always @(posedge clk or negedge running) begin
        if (!running) begin
            h <= 8'd0;
            row_band <= 5'd0; remaining <= 7'd75;
            r <= 2'd0;
            g <= 2'd0;
            b <= 2'd0;
            hsync <= 1'b1;
            vsync <= 1'b1;
        end else begin
            if (h == 8'd199) begin
                h <= 8'd0;
                if (remaining != 0) remaining <= remaining - 1'b1;
                else begin
                    case (row_band)
                        5'd0: begin remaining <= 7'd23; row_band <= 5'd1; end
                        5'd1: begin remaining <= 7'd31; row_band <= 5'd2; end
                        5'd2: begin remaining <= 7'd11; row_band <= 5'd3; end
                        5'd3: begin remaining <= 7'd23; row_band <= 5'd4; end
                        5'd4: begin remaining <= 7'd11; row_band <= 5'd5; end
                        5'd5: begin remaining <= 7'd35; row_band <= 5'd6; end
                        5'd6: begin remaining <= 7'd7; row_band <= 5'd7; end
                        5'd7: begin remaining <= 7'd23; row_band <= 5'd8; end
                        5'd8: begin remaining <= 7'd11; row_band <= 5'd9; end
                        5'd9: begin remaining <= 7'd35; row_band <= 5'd10; end
                        5'd10: begin remaining <= 7'd11; row_band <= 5'd11; end
                        5'd11: begin remaining <= 7'd23; row_band <= 5'd12; end
                        5'd12: begin remaining <= 7'd11; row_band <= 5'd13; end
                        5'd13: begin remaining <= 7'd31; row_band <= 5'd14; end
                        5'd14: begin remaining <= 7'd23; row_band <= 5'd15; end
                        5'd15: begin remaining <= 7'd79; row_band <= 5'd16; end
                        5'd16: begin remaining <= 7'd9; row_band <= 5'd17; end
                        5'd17: begin remaining <= 7'd1; row_band <= 5'd18; end
                        5'd18: begin remaining <= 7'd32; row_band <= 5'd19; end
                        5'd19: begin remaining <= 7'd75; row_band <= 5'd0; end
                        default: begin remaining <= 7'd75; row_band <= 5'd0; end
                    endcase
                end
            end else h <= h + 8'd1;
            hsync <= !((h >= 8'd164) && (h < 8'd188));
            vsync <= !(row_band == 5'd18);
            {r,g,b} <= active ? logo_rgb : 6'b000000;
        end
    end
endmodule
`default_nettype wire
