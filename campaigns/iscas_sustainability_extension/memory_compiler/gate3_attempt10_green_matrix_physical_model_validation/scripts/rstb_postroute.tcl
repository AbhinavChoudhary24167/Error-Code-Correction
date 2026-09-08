set root /work/campaigns/iscas_sustainability_extension/memory_compiler
set prior $root/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure
set design $::env(RSTB_DESIGN)
read_liberty $prior/raw/liberty/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty $prior/raw/liberty/sram22_256x64m4w8_tt_025C_1v80.lib
read_liberty $prior/raw/liberty/sram22_256x8m8w1_tt_025C_1v80.lib
set result $prior/raw/openroad/work/results/sky130hd/attempt09_${design}/seed11
read_db $result/6_final.odb
read_sdc $result/6_final.sdc
read_spef $result/6_final.spef
set block [ord::get_db_block]
if {$design eq "u0"} {
  set targets {{u_data/rstb hold151 X}}
} else {
  set targets {{u_protected_memory.u_data/rstb hold824 X} {u_protected_memory.u_ecc/rstb attempt09_ecc_rstb_stage2 Y}}
}
foreach item $targets {
  lassign $item target driver output
  puts "RSTB_EXTRACTED_BEGIN design=$design target=$target driver=$driver"
  report_slews -digits 9 [get_pins $driver/A]
  report_slews -digits 9 [get_pins $driver/$output]
  report_slews -digits 9 [get_pins $target]
  report_net [get_full_name [get_nets -of_objects [get_pins $target]]]
  set inst [$block findInst $driver]
  puts "RSTB_DRIVER_LOCATION_DBU [$inst getLocation] orientation=[$inst getOrient]"
  puts "RSTB_DRIVER_PIN_XY_DBU [[$inst findITerm $output] getAvgXY]"
  set slash [string last / $target]
  set macro [$block findInst [string range $target 0 [expr {$slash-1}]]]
  puts "RSTB_MACRO_PIN_XY_DBU [[$macro findITerm rstb] getAvgXY]"
  puts RSTB_EXTRACTED_END
}
