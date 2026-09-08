foreach name [list ATTEMPT09_DESIGN ATTEMPT09_TARGET ATTEMPT09_CELL] {
  if { ![info exists ::env($name)] } {
    puts stderr "$name is required"
    exit 2
  }
}

set design $::env(ATTEMPT09_DESIGN)
set target $::env(ATTEMPT09_TARGET)
set cell $::env(ATTEMPT09_CELL)
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
if { [llength $target_pin] != 1 || [llength $target_net] != 1 } {
  puts stderr "Target must resolve to one pin and one net: $target"
  exit 3
}

puts "ATTEMPT09_EXPERIMENT design=$design target=$target cell=$cell"
puts "ATTEMPT09_BEFORE"
report_slews -digits 9 $target_pin
report_net [get_full_name $target_net]

set safe_target [string map [list . _ / _ {[} _ {]} _] $target]
set inv1 "attempt09_diag_${safe_target}_inv1"
set inv2 "attempt09_diag_${safe_target}_inv2"
set mid1 "attempt09_diag_${safe_target}_mid1"
set mid2 "attempt09_diag_${safe_target}_mid2"

set db [ord::get_db]
set block [ord::get_db_block]
set master [$db findMaster $cell]
set slash [string last "/" $target]
set target_inst_name [string range $target 0 [expr {$slash - 1}]]
set target_term_name [string range $target [expr {$slash + 1}] end]
set target_inst [$block findInst $target_inst_name]
set target_iterm [$target_inst findITerm $target_term_name]
set target_dbnet [$target_iterm getNet]
set dbnet1 [odb::dbNet_create $block $mid1]
set dbnet2 [odb::dbNet_create $block $mid2]
set dbinv1 [odb::dbInst_create $block $master $inv1]
set dbinv2 [odb::dbInst_create $block $master $inv2]
set input_terms [list A]
if { [regexp {__nand2_} $cell] } {
  set input_terms [list A B]
} elseif { [regexp {__nand3_} $cell] } {
  set input_terms [list A B C]
} elseif { [regexp {__nand4_} $cell] } {
  set input_terms [list A B C D]
}
foreach term_name $input_terms {
  [$dbinv1 findITerm $term_name] connect $target_dbnet
}
[$dbinv1 findITerm Y] connect $dbnet1
foreach term_name $input_terms {
  [$dbinv2 findITerm $term_name] connect $dbnet1
}
[$dbinv2 findITerm Y] connect $dbnet2
$target_iterm disconnect
$target_iterm connect $dbnet2

lassign [$target_iterm getAvgXY] target_placed target_x target_y
if { $target_placed } {
  $dbinv1 setLocation [expr {$target_x - 12000}] [expr {$target_y - 3000}]
  $dbinv2 setLocation [expr {$target_x - 6000}] [expr {$target_y - 3000}]
  $dbinv1 setPlacementStatus PLACED
  $dbinv2 setPlacementStatus PLACED
}
estimate_parasitics -placement

puts "ATTEMPT09_AFTER"
report_slews -digits 9 [get_pins $target]
report_slews -digits 9 [get_pins "$inv1/A"]
report_slews -digits 9 [get_pins "$inv2/A"]
report_check_types -max_slew -violators
report_checks -path_delay max -fields {slew cap input_pins nets fanout} -format full_clock_expanded -digits 6 -group_count 1
report_checks -path_delay min -fields {slew cap input_pins nets fanout} -format full_clock_expanded -digits 6 -group_count 1
