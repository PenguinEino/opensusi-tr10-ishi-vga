puts "=== Additional electrical checks: ideal clock ==="
check_setup -verbose
report_check_types -max_capacitance -max_slew -violators -digits 6
report_net clk_buf
puts "=== Cell-propagated clock, no interconnect RC ==="
set_propagated_clock [all_clocks]
set_input_transition 1.2 [get_ports clk]
report_check_types -max_capacitance -max_slew -violators -digits 6
report_checks -path_delay min_max -format full_clock_expanded -fields {slew cap fanout} -digits 6 -group_path_count 2
report_clock_min_period
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -format full_clock_expanded -fields {slew cap fanout} -digits 6
