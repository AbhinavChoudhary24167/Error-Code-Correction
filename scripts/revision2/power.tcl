source $::env(SCRIPTS_DIR)/load.tcl
load_design 6_final.odb 6_final.sdc
read_spef $::env(RESULTS_DIR)/6_final.spef

file mkdir $::env(REV2_POWER_DIR)
set label $::env(REV2_POWER_LABEL)
set vcd_path $::env(REV2_POWER_VCD)
puts "REV2_POWER_TRACE label=$label vcd=$vcd_path"
read_vcd -scope gate04_trace_top $vcd_path
report_activity_annotation > $::env(REV2_POWER_DIR)/${label}.annotation.rpt
report_activity_annotation -report_annotated > $::env(REV2_POWER_DIR)/${label}.annotated.rpt
report_activity_annotation -report_unannotated > $::env(REV2_POWER_DIR)/${label}.unannotated.rpt
report_power -digits 12 > $::env(REV2_POWER_DIR)/${label}.power.rpt
report_power -format json > $::env(REV2_POWER_DIR)/${label}.native-rounded.power.json
puts "REV2_POWER_PASS"
