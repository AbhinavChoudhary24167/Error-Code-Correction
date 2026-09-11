set operation $::env(ACTIVITY_OPERATION)
read_liberty /OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty /repo/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib
read_liberty /repo/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib
set root /campaign-run/results/sky130hd/secded_matched_sram_top/clk10p0ns_seed11
read_db $root/6_final.odb
read_sdc $root/6_final.sdc
read_spef $root/6_final.spef
read_vcd -scope tb/dut /campaign-run/activity/${operation}.vcd
source /campaign-run/power_explicit_activity/remediation03/${operation}/routed_net_activity.tcl
report_power > /dev/null
foreach pin {_393_/A _393_/Y _394_/A u_data/dout[45]} {
  set objects [get_pins -quiet $pin]
  if {[llength $objects] > 0} {
    puts "GREEN_V33_ACTIVITY_PROPERTY operation=$operation pin=$pin value=[get_property -object_type pin $pin activity]"
  } else {
    puts "GREEN_V33_ACTIVITY_PROPERTY operation=$operation pin=$pin value=PIN_NOT_FOUND"
  }
}
