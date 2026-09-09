read_liberty /OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty /repo/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib
read_liberty /repo/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib
read_db /campaign-run/results/sky130hd/secded_matched_sram_top/clk10p0ns_seed11/6_final.odb
read_sdc /campaign-run/results/sky130hd/secded_matched_sram_top/clk10p0ns_seed11/6_final.sdc
read_spef /campaign-run/results/sky130hd/secded_matched_sram_top/clk10p0ns_seed11/6_final.spef
read_vcd -scope tb/dut /campaign-run/activity/IDLE.vcd
report_activity_annotation > /campaign-run/power/IDLE/annotation.rpt
report_activity_annotation -report_annotated > /campaign-run/power/IDLE/annotated.rpt
report_activity_annotation -report_unannotated > /campaign-run/power/IDLE/unannotated.rpt
report_power -digits 12 > /campaign-run/power/IDLE/power.rpt
report_power -format json > /campaign-run/power/IDLE/power.json
report_power -instances [get_cells {u_data u_ecc0}] -digits 12 > /campaign-run/power/IDLE/macros.power.rpt
puts "GREEN_V33_POWER_COMPLETE architecture=secded_matched_sram_top operation=IDLE"
