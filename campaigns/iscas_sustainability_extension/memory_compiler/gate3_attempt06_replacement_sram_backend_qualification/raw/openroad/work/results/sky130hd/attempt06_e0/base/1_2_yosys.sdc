create_clock -name core_clk -period 10.0 [get_ports clk]
set_clock_uncertainty 0.10 [get_clocks core_clk]
set_input_delay 0.50 -clock core_clk [get_ports {rstb ce we addr[*] payload_in[*]}]
set_output_delay 0.50 -clock core_clk [get_ports {payload_out[*] correction_applied detected_uncorrectable}]
set_load 0.02 [get_ports {payload_out[*] correction_applied detected_uncorrectable}]
# Match U0's design-level bound.  Published macro-pin limits remain untouched.
set_max_transition 0.60 [current_design]
