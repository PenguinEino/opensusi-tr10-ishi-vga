`default_nettype none
// Explicit rPLL instantiation for the pinned open-source FPGA flow.
// Equivalent divider settings to docs/FPGA_BRINGUP.md; NOT IP Generator output.
// 27 / 3 * 7 = 63 MHz; VCO = 63 * 16 = 1008 MHz; CLKOUTD = 63 / 20.
module gowin_pll_315(input wire clkin, output wire clkout, clkoutd, lock);
    rPLL #(
        .FCLKIN("27"), .IDIV_SEL(2), .FBDIV_SEL(6), .ODIV_SEL(16),
        .DYN_SDIV_SEL(20), .CLKFB_SEL("internal"),
        .DYN_IDIV_SEL("false"), .DYN_FBDIV_SEL("false"),
        .DYN_ODIV_SEL("false"), .DYN_DA_EN("false"),
        .CLKOUT_BYPASS("false"), .CLKOUTP_BYPASS("false"),
        .CLKOUTD_BYPASS("false"), .CLKOUTD_SRC("CLKOUT"),
        .CLKOUTD3_SRC("CLKOUT"), .PSDA_SEL("0000"),
        .DUTYDA_SEL("1000"), .DEVICE("GW2A-18")
    ) pll (
        .CLKIN(clkin), .CLKOUT(clkout), .CLKOUTD(clkoutd), .LOCK(lock),
        .CLKOUTP(), .CLKOUTD3(), .CLKFB(1'b0),
        .RESET(1'b0), .RESET_P(1'b0),
        .FBDSEL(6'b0), .IDSEL(6'b0), .ODSEL(6'b0),
        .PSDA(4'b0), .DUTYDA(4'b0), .FDLY(4'b0)
    );
endmodule
`default_nettype wire
