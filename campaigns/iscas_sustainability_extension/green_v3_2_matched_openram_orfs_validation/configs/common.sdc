set clk_period $::env(CLOCK_PERIOD)
create_clock -name core_clk -period $clk_period [get_ports clk]
set_clock_uncertainty 0.10 [get_clocks core_clk]
set non_clock_inputs [lsearch -inline -all -not -exact [all_inputs] [get_ports clk]]
set_input_delay [expr {$clk_period * 0.10}] -clock core_clk $non_clock_inputs
set_output_delay [expr {$clk_period * 0.10}] -clock core_clk [all_outputs]
set_load 0.02 [all_outputs]
set_max_transition 0.60 [current_design]
