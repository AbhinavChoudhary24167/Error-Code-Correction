foreach required {ATTEMPT10_MODEL ATTEMPT10_DESIGN ATTEMPT10_SEED} {
  if { ![info exists ::env($required)] } {
    puts stderr "$required is required"
    exit 2
  }
}
set model $::env(ATTEMPT10_MODEL)
set design $::env(ATTEMPT10_DESIGN)
set seed $::env(ATTEMPT10_SEED)
set suffix ""
if { [info exists ::env(ATTEMPT10_RUN_SUFFIX)] } { set suffix $::env(ATTEMPT10_RUN_SUFFIX) }
set campaign "/work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation"
set prior "/work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"
set external "/attempt10-work"

read_liberty /OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty "$campaign/liberty/$model/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib"
if { $design == "e0" } {
  read_liberty "$campaign/liberty/$model/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib"
}
set results "$external/results/sky130hd/attempt10_${model}_${design}${suffix}/seed${seed}"
read_db "$results/6_final.odb"
read_sdc "$results/6_final.sdc"
read_spef "$results/6_final.spef"

puts "ATTEMPT10_SLEW_DETAIL_BEGIN model=$model design=$design seed=$seed"
if { $design == "u0" } {
  set patterns [list {u_data/dout[*]} {u_data/rstb} {u_data/clk}]
} else {
  set patterns [list {u_protected_memory.u_data/dout[*]} {u_protected_memory.u_ecc/dout[*]} {u_protected_memory.u_data/rstb} {u_protected_memory.u_data/clk} {u_protected_memory.u_ecc/rstb} {u_protected_memory.u_ecc/clk}]
}
foreach pattern $patterns {
  puts "ATTEMPT10_PATTERN $pattern"
  foreach pin [get_pins $pattern] {
    report_slews -digits 9 $pin
  }
}
puts "ATTEMPT10_SLEW_DETAIL_END model=$model design=$design seed=$seed"
