set root /work/campaigns/iscas_sustainability_extension/memory_compiler
set prior $root/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure
set current $root/gate3_attempt10_green_matrix_physical_model_validation
set macro $::env(RSTB_MACRO)
set family $::env(RSTB_FAMILY)
read_liberty $prior/raw/liberty/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty $prior/raw/liberty/${macro}_tt_025C_1v80.lib
read_verilog $current/rstb/diagnostics/${macro}_${family}.v
link_design diagnostic
create_clock -name diagnostic_clk -period 10 [get_ports clk]
set_input_delay 0 -clock diagnostic_clk [get_ports rstb]
puts "RSTB_ZERO_WIRE_BEGIN macro=$macro family=$family"
foreach slew {0.01 0.1 0.3} {
  set_input_transition $slew [get_ports rstb]
  puts "RSTB_INPUT_SLEW_NS $slew"
  report_slews -digits 9 [get_pins stage2/A]
  if {$family eq "inv" || $family eq "clkinv"} {
    report_slews -digits 9 [get_pins stage1/A]
    report_slews -digits 9 [get_pins stage1/Y]
    report_slews -digits 9 [get_pins stage2/Y]
  } else {
    report_slews -digits 9 [get_pins stage2/X]
  }
  report_slews -digits 9 [get_pins memory/rstb]
  report_net local_rstb
}
puts RSTB_ZERO_WIRE_END
