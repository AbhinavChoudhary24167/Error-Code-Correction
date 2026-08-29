source $::env(SCRIPTS_DIR)/load.tcl
load_design 6_final.odb 6_final.sdc
read_spef $::env(RESULTS_DIR)/6_final.spef

file mkdir $::env(BREADTH_POWER_DIR)
set label $::env(BREADTH_POWER_LABEL)
set vcd_path $::env(BREADTH_POWER_VCD)
puts "BREADTH_POWER_TRACE label=$label vcd=$vcd_path"
read_vcd -scope gate04_trace_top $vcd_path
report_activity_annotation > $::env(BREADTH_POWER_DIR)/${label}.annotation.rpt
report_activity_annotation -report_annotated > $::env(BREADTH_POWER_DIR)/${label}.annotated.rpt
report_activity_annotation -report_unannotated > $::env(BREADTH_POWER_DIR)/${label}.unannotated.rpt
report_power -digits 12 > $::env(BREADTH_POWER_DIR)/${label}.power.rpt
report_power -format json > $::env(BREADTH_POWER_DIR)/${label}.native-rounded.power.json
puts "BREADTH_POWER_PASS"
