# Design-owned mandatory checks, appended after the requested upstream report.
# No wire RC is implied. Input waveform/load assumptions remain in config/Tcl.
puts "ISHI_STA_GATE_BEGIN"
apply_period $PER
set_propagated_clock [all_clocks]
puts "ISHI_STA_CLOCKS [llength [all_clocks]]"
puts "ISHI_STA_REG_CLOCKS [llength [all_registers -clock_pins]]"
puts "ISHI_STA_REG_DATA [llength [all_registers -data_pins]]"
check_setup -verbose
foreach {label mode target} [list SETUP max [all_registers -data_pins] HOLD min [all_registers -data_pins] OUTPUT max [all_outputs]] {
    set paths [find_timing_paths -path_delay $mode -from [all_registers -clock_pins] -to $target -group_path_count 1]
    if {[llength $paths] == 0} { error "ISHI_STA missing $label path" }
    puts "ISHI_STA_${label} [get_property [lindex $paths 0] slack]"
    report_checks -path_delay $mode -from [all_registers -clock_pins] -to $target -format full_clock_expanded -fields {slew cap fanout} -digits 6 -group_path_count 1
}
puts "ISHI_STA_ELECTRICAL_BEGIN"
report_check_types -max_capacitance -max_slew -min_pulse_width -min_period -violators -digits 6
puts "ISHI_STA_ELECTRICAL_END"
report_clock_min_period
puts "ISHI_STA_GATE_END"
