if { ![info exists ::env(ATTEMPT09_DESIGN)] } {
  puts stderr "ATTEMPT09_DESIGN must be u0 or e0"
  exit 2
}

set design $::env(ATTEMPT09_DESIGN)
set root "/work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"
set diag "$root/raw/diagnostics/class_c_counterfactual"

read_liberty /OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty "$diag/liberty/sram22_256x64m4w8_tt_025C_1v80.lib"
if { $design == "e0" } {
  read_liberty "$diag/liberty/sram22_256x8m8w1_tt_025C_1v80.lib"
}
set results "$root/raw/openroad/work/results/sky130hd/attempt09_${design}/seed11"
read_db "$results/6_final.odb"
read_sdc "$results/6_final.sdc"
read_spef "$results/6_final.spef"

puts "ATTEMPT09_CLASS_C_COUNTERFACTUAL_BEGIN design=$design seed=11"
puts "DIAGNOSTIC_ONLY production_netlist_placement_routing_sdc_spef_unchanged=true"
puts "ONLY_EXCLUDED_RULE inherited_SRAM22_output_default_max_transition_0p04=true"
report_check_types -max_slew -violators -digits 9
puts "ATTEMPT09_CLASS_C_COUNTERFACTUAL_END design=$design seed=11"
