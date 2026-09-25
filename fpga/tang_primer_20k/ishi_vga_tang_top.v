`default_nettype none
// FPGA-only wrapper. Generate gowin_pll_315 with Gowin IP Core Generator:
// CLKIN=27 MHz, CLKOUT=63 MHz, CLKOUTD=CLKOUT/20=3.15 MHz, LOCK enabled.
// No reset ports, no dynamic controls. See docs/FPGA_BRINGUP.md.
module ishi_vga_tang_top (
    input  wire clk_27m,
    output wire r, g, b, hsync, vsync,
    output wire pll_lock_mon,
    output wire clk_315_mon
);
    wire clk_315;

    gowin_pll_315 u_pll (
        .clkin(clk_27m),
        .clkout(),
        .clkoutd(clk_315),
        .lock(pll_lock_mon)
    );

    assign clk_315_mon = clk_315;

    // Use the adopted, reset-free ASIC RTL without FPGA initialization edits.
    // LOCK is observable only; it does not gate the core clock.
    ishi_vga_core u_core (
        .clk(clk_315),
        .r(r), .g(g), .b(b),
        .hsync(hsync), .vsync(vsync)
    );
endmodule
`default_nettype wire
