source $::env(SCRIPTS_DIR)/load.tcl
load_design 6_final.odb 6_final.sdc
read_spef $::env(RESULTS_DIR)/6_final.spef

file mkdir $::env(GATE04_POWER_DIR)
foreach spec [split $::env(GATE04_TRACE_SPECS) ","] {
  set pieces [split $spec "|"]
  set label [lindex $pieces 0]
  set vcd_path [lindex $pieces 1]
  puts "GATE04_POWER_TRACE label=$label vcd=$vcd_path"
  read_vcd -scope gate04_trace_top $vcd_path
  report_activity_annotation > $::env(GATE04_POWER_DIR)/${label}.annotation.rpt
  report_activity_annotation -report_annotated > $::env(GATE04_POWER_DIR)/${label}.annotated.rpt
  report_activity_annotation -report_unannotated > $::env(GATE04_POWER_DIR)/${label}.unannotated.rpt
  report_power -digits 12 > $::env(GATE04_POWER_DIR)/${label}.power.rpt
  report_power -format json > $::env(GATE04_POWER_DIR)/${label}.native-rounded.power.json
}
puts "GATE04_POWER_PASS"
