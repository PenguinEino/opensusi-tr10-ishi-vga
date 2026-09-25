`default_nettype none
// Dock L14 LED, 0.5 s on / 0.5 s off from the 27 MHz oscillator.
// FPGA bring-up only; initialization does not modify the ASIC core.
module led_top(input wire clk_27m, output reg led = 1'b1);
    reg [23:0] count = 24'd0;
    always @(posedge clk_27m) begin
        if (count == 24'd13499999) begin
            count <= 24'd0;
            led <= ~led;
        end else count <= count + 1'b1;
    end
endmodule
`default_nettype wire
