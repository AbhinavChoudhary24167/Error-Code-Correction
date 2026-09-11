# Additive diagnostic: make VCD-measured SRAM outputs activity roots by
# disabling macro timing arcs only inside this power-analysis process.
set out /repo/campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/diagnostics/macro_root_activity_sensitivity
file mkdir $out
read_liberty /OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty /repo/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib
read_liberty /repo/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib
set root /campaign-run/results/sky130hd/secded_matched_sram_top/clk10p0ns_seed11
read_db $root/6_final.odb
read_sdc $root/6_final.sdc
read_spef $root/6_final.spef
set_disable_timing [get_cells {u_data u_ecc0}]

set_power_activity -pins {u_data/dout[45] _393_/A _393_/Y} -density 0.000001 -duty 0.1
report_activity_annotation -report_annotated > $out/low.annotated.rpt
report_power -digits 12 > $out/low.power.rpt
report_power -instances [get_cells {_393_}] -digits 12 > $out/low.instance.power.rpt
foreach pin {u_data/dout[45] _393_/A _393_/Y} {
  puts "GREEN_V33_MACRO_ROOT_LOW pin=$pin value=[get_property -object_type pin $pin activity]"
}

set_power_activity -pins {u_data/dout[45] _393_/A _393_/Y} -density 0.1 -duty 0.9
report_activity_annotation -report_annotated > $out/high.annotated.rpt
report_power -digits 12 > $out/high.power.rpt
report_power -instances [get_cells {_393_}] -digits 12 > $out/high.instance.power.rpt
foreach pin {u_data/dout[45] _393_/A _393_/Y} {
  puts "GREEN_V33_MACRO_ROOT_HIGH pin=$pin value=[get_property -object_type pin $pin activity]"
}
