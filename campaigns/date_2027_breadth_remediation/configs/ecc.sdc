set clk_period $::env(CLOCK_PERIOD)
create_clock -name clk_i -period $clk_period [get_ports clk_i]
set non_clock_inputs [lsearch -inline -all -not -exact [all_inputs] [get_ports clk_i]]
set_input_delay [expr {$clk_period * 0.10}] -clock clk_i $non_clock_inputs
set_output_delay [expr {$clk_period * 0.10}] -clock clk_i [all_outputs]
set_load 0.05 [all_outputs]
