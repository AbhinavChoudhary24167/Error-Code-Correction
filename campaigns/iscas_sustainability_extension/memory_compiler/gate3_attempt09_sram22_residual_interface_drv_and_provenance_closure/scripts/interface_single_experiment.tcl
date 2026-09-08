foreach name [list ATTEMPT09_DESIGN ATTEMPT09_TARGET ATTEMPT09_CELL ATTEMPT09_INPUTS ATTEMPT09_OUTPUT] {
  if { ![info exists ::env($name)] } {
    puts stderr "$name is required"
    exit 2
  }
}

set design $::env(ATTEMPT09_DESIGN)
set target $::env(ATTEMPT09_TARGET)
set cell $::env(ATTEMPT09_CELL)
set input_terms [split $::env(ATTEMPT09_INPUTS) ,]
set output_term $::env(ATTEMPT09_OUTPUT)
set prior "/work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt08_sram22_slew_provenance_and_drv_closure"

read_liberty /OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty "$prior/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib"
if { $design eq "e0" } {
  read_liberty "$prior/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib"
}
set results "$prior/raw/openroad/work/results/sky130hd/attempt08_${design}/seed11"
read_db "$results/6_final.odb"
read_sdc "$results/6_final.sdc"
read_spef "$results/6_final.spef"

set target_pin [get_pins $target]
set target_net [get_nets -of_objects $target_pin]
puts "ATTEMPT09_EXPERIMENT design=$design target=$target cell=$cell inputs=$input_terms output=$output_term"
puts "ATTEMPT09_BEFORE"
report_slews -digits 9 $target_pin
report_net [get_full_name $target_net]

set safe_target [string map [list . _ / _ {[} _ {]} _] $target]
set inst_name "attempt09_diag_${safe_target}_single"
set new_net_name "attempt09_diag_${safe_target}_out"
set db [ord::get_db]
set block [ord::get_db_block]
set master [$db findMaster $cell]
set slash [string last "/" $target]
set target_inst_name [string range $target 0 [expr {$slash - 1}]]
set target_term_name [string range $target [expr {$slash + 1}] end]
set target_inst [$block findInst $target_inst_name]
set target_iterm [$target_inst findITerm $target_term_name]
set target_dbnet [$target_iterm getNet]
set new_dbnet [odb::dbNet_create $block $new_net_name]
set new_inst [odb::dbInst_create $block $master $inst_name]
foreach term_name $input_terms {
  [$new_inst findITerm $term_name] connect $target_dbnet
}
[$new_inst findITerm $output_term] connect $new_dbnet
$target_iterm disconnect
$target_iterm connect $new_dbnet

lassign [$target_iterm getAvgXY] target_placed target_x target_y
if { $target_placed } {
  $new_inst setLocation [expr {$target_x - 6000}] [expr {$target_y - 3000}]
  $new_inst setPlacementStatus PLACED
}
estimate_parasitics -placement

puts "ATTEMPT09_AFTER"
report_slews -digits 9 [get_pins $target]
report_check_types -max_slew -violators
report_checks -path_delay max -fields {slew cap input_pins nets fanout} -format full_clock_expanded -digits 6 -group_count 1
report_checks -path_delay min -fields {slew cap input_pins nets fanout} -format full_clock_expanded -digits 6 -group_count 1
