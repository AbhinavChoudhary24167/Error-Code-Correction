create_clock -name core_clk -period 10.0 [get_ports clk]
set_clock_uncertainty 0.10 [get_clocks core_clk]
set_input_delay 0.50 -clock core_clk [get_ports {rstb ce we wmask[*] addr[*] data_in[*]}]
set_output_delay 0.50 -clock core_clk [get_ports {data_out[*]}]
set_load 0.02 [get_ports {data_out[*]}]
# This design-level bound is intentionally looser than the immutable SRAM22
# rstb pin limit; the latter is preserved and reported rather than patched.
set_max_transition 0.60 [current_design]
