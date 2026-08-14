# Gate-03 pilot constraints; not final paper settings.
create_clock -name gate03_clock -period 10.0 [get_ports clk]
set_clock_uncertainty 0.5 [get_clocks gate03_clock]
set non_clock_inputs [remove_from_collection [all_inputs] [get_ports clk]]
set_input_delay 1.0 -clock gate03_clock $non_clock_inputs
set_output_delay 1.0 -clock gate03_clock [all_outputs]
set_input_transition 0.2 $non_clock_inputs
set_load 0.05 [all_outputs]
set_max_fanout 16 [current_design]
set_max_transition 1.0 [current_design]
set_max_capacitance 0.2 [current_design]
