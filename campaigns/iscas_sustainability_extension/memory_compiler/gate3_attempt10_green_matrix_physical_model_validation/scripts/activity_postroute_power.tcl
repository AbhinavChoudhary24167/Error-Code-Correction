# Read-only diagnostic on frozen final state. This does not qualify energy.
set design $::env(ACTIVITY_DESIGN)
set family $::env(ACTIVITY_FAMILY)
set root /work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure
set arch [string toupper $design]
set out /output/postroute/${family}/${arch}/slash_scope
file mkdir $out
read_liberty /OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty $root/raw/liberty/sram22_256x64m4w8_tt_025C_1v80.lib
if {$design eq "e0"} {read_liberty $root/raw/liberty/sram22_256x8m8w1_tt_025C_1v80.lib}
set result $root/raw/openroad/work/results/sky130hd/attempt09_${design}/seed11
read_db $result/6_final.odb
read_sdc $result/6_final.sdc
read_spef $result/6_final.spef
help report_power > $out/report_power.help.txt
help read_vcd > $out/read_vcd.help.txt
help report_activity_annotation > $out/report_activity_annotation.help.txt
read_vcd -scope tb/dut /output/raw/${family}/${arch}/activity.vcd
report_activity_annotation > $out/annotation.rpt
report_activity_annotation -report_annotated > $out/annotated.rpt
report_activity_annotation -report_unannotated > $out/unannotated.rpt
report_power -digits 12 > $out/power.rpt
report_power -format json > $out/power.json
set macro_pattern {u_data}
if {$design eq "e0"} {set macro_pattern {u_protected_memory.u_data u_protected_memory.u_ecc}}
report_power -instances [get_cells $macro_pattern] -digits 12 > $out/macros.power.rpt
puts "ATTEMPT10_POSTROUTE_ACTIVITY_DIAGNOSTIC_COMPLETE architecture=$arch family=$family seed=11 model=UPSTREAM_ORIGINAL"
