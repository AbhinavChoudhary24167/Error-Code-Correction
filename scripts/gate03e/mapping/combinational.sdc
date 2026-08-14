set clk_period 10.0
create_clock -name virtual_clk -period $clk_period
set_input_delay 0 -clock virtual_clk [all_inputs]
set_output_delay 0 -clock virtual_clk [all_outputs]
