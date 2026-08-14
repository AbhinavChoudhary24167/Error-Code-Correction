set clk_period 10.0
create_clock -name clk_i -period $clk_period [get_ports clk_i]
set_input_delay 0 -clock clk_i [lsearch -inline -all -not -exact [all_inputs] [get_ports clk_i]]
set_output_delay 0 -clock clk_i [all_outputs]
