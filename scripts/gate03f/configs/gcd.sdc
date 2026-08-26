set clk_period $::env(CLOCK_PERIOD)
create_clock -name clk -period $clk_period [get_ports clk]
set non_clock_inputs [lsearch -inline -all -not -exact [all_inputs] [get_ports clk]]
set_input_delay [expr {$clk_period * 0.10}] -clock clk $non_clock_inputs
set_output_delay [expr {$clk_period * 0.10}] -clock clk [all_outputs]
set_load 0.05 [all_outputs]
