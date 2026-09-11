read_liberty /OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty /repo/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib
read_liberty /repo/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib
read_db /campaign-run/results/sky130hd/secded_matched_sram_top/clk10p0ns_seed11/6_final.odb
set green_v33_activity_roots [dict create]
set green_v33_activity_root_count 0
set green_v33_activity_root_annotation_count 0
set green_v33_block [ord::get_db_block]
foreach green_v33_macro_name {u_data u_ecc0} {
  set green_v33_macro [$green_v33_block findInst $green_v33_macro_name]
  if {$green_v33_macro == "NULL"} {
    error "GREEN v3.3 activity-root macro not found: $green_v33_macro_name"
  }
  foreach green_v33_iterm [$green_v33_macro getITerms] {
    set green_v33_mterm [$green_v33_iterm getMTerm]
    if {[$green_v33_mterm getIoType] == "OUTPUT"} {
      set green_v33_net [$green_v33_iterm getNet]
      if {$green_v33_net != "NULL"} {
        set green_v33_net_name [$green_v33_net getName]
        set green_v33_port_name [format "green_v33_activity_root_%03d" $green_v33_activity_root_count]
        dict set green_v33_activity_roots $green_v33_net_name $green_v33_port_name
        $green_v33_iterm disconnect
        set green_v33_bterm [odb::dbBTerm_create $green_v33_net $green_v33_port_name]
        $green_v33_bterm setSigType SIGNAL
        $green_v33_bterm setIoType INPUT
        incr green_v33_activity_root_count
      }
    }
  }
}
puts "GREEN_V33_MACRO_OUTPUT_ACTIVITY_ROOTS count=$green_v33_activity_root_count"
read_sdc /campaign-run/results/sky130hd/secded_matched_sram_top/clk10p0ns_seed11/6_final.sdc
read_spef /campaign-run/results/sky130hd/secded_matched_sram_top/clk10p0ns_seed11/6_final.spef
read_vcd -scope tb/dut /campaign-run/activity/WRITE_CLEAN.vcd
source /campaign-run/power_explicit_activity/remediation06/WRITE_CLEAN/routed_net_activity.tcl
puts "GREEN_V33_MACRO_OUTPUT_ACTIVITY_ROOT_ANNOTATIONS count=$green_v33_activity_root_annotation_count"
report_activity_annotation > /campaign-run/power_explicit_activity/remediation06/WRITE_CLEAN/annotation.rpt
report_activity_annotation -report_annotated > /campaign-run/power_explicit_activity/remediation06/WRITE_CLEAN/annotated.rpt
report_activity_annotation -report_unannotated > /campaign-run/power_explicit_activity/remediation06/WRITE_CLEAN/unannotated.rpt
report_power -digits 12 > /campaign-run/power_explicit_activity/remediation06/WRITE_CLEAN/power.rpt
report_power -format json > /campaign-run/power_explicit_activity/remediation06/WRITE_CLEAN/power.json
report_power -instances [get_cells {u_data u_ecc0}] -digits 12 > /campaign-run/power_explicit_activity/remediation06/WRITE_CLEAN/macros.power.rpt
puts "GREEN_V33_POWER_COMPLETE architecture=secded_matched_sram_top operation=WRITE_CLEAN"
