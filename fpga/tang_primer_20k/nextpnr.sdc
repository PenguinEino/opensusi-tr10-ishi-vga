# nextpnr does not derive rPLL CLKOUTD in this pinned build.
create_clock -name clk_27m -period 37.037037 [get_ports {clk_27m}]
create_clock -name clk_315 -period 317.460317 [get_nets {clk_315}]
