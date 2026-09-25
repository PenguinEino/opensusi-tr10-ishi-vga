create_clock -name clk_27m -period 37.037037 [get_ports {clk_27m}]

# Gowin derives PLL clocks from the input clock and primitive parameters.
# Confirm CLKOUTD = 317.460317 ns / 3.15 MHz in Clock Summary after P&R.
# This constrains internal logic; VGA analog loading is checked on the board.
