set_propagated_clock [all_clocks]
foreach n {clk_buf clk_row0 clk_row1 clk_row2 clk_row3} { report_net $n }
report_clock_skew -setup -digits 6
report_clock_skew -hold -digits 6
report_checks -path_delay min_max -format full_clock_expanded -fields {slew cap fanout} -digits 6
