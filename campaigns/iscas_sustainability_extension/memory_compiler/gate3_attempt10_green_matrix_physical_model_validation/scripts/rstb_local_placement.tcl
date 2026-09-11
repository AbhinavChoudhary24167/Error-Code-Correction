# Controlled electrical/legal-cell diagnostic. No ODB/netlist is written.
set here /work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation
source $here/scripts/rstb_postroute.tcl
source /OpenROAD-flow-scripts/flow/platforms/sky130hd/setRC.tcl
# The frozen final ODB contains fill cells; remove them only from this in-memory
# diagnostic before adding cells, so detailed placement has usable whitespace.
remove_fillers
set target $::env(RSTB_TARGET)
set db [ord::get_db]
set slash [string last / $target]
set macro [$block findInst [string range $target 0 [expr {$slash-1}]]]
set target_iterm [$macro findITerm rstb]
set upstream [$target_iterm getNet]
set master [$db findMaster sky130_fd_sc_hd__clkinv_16]
set first [odb::dbInst_create $block $master rstb10_first]
set final [odb::dbInst_create $block $master rstb10_final]
set mid [odb::dbNet_create $block rstb10_mid]
set out [odb::dbNet_create $block rstb10_out]
[$first findITerm A] connect $upstream
[$first findITerm Y] connect $mid
[$final findITerm A] connect $mid
[$final findITerm Y] connect $out
$target_iterm disconnect
$target_iterm connect $out
lassign [$target_iterm getAvgXY] placed target_x target_y
$first setLocation [expr {$target_x+12000}] [expr {$target_y-3000}]
$final setLocation [expr {$target_x+3000}] [expr {$target_y-3000}]
$first setPlacementStatus PLACED
$final setPlacementStatus PLACED
puts "RSTB_LOCAL_BEGIN target=$target cell=sky130_fd_sc_hd__clkinv_16 stages=2"
puts RSTB_IDEALIZED_BEFORE_LEGALIZATION
estimate_parasitics -placement
report_slews -digits 9 [get_pins rstb10_first/A]
report_slews -digits 9 [get_pins rstb10_final/A]
report_slews -digits 9 [get_pins rstb10_final/Y]
report_slews -digits 9 [get_pins $target]
puts "RSTB_FINAL_PIN_XY_DBU [[$final findITerm Y] getAvgXY]"
puts "RSTB_MACRO_PIN_XY_DBU [$target_iterm getAvgXY]"
report_net rstb10_out
puts RSTB_LEGALIZED_PLACEMENT
detailed_placement
check_placement -verbose
estimate_parasitics -placement
report_slews -digits 9 [get_pins rstb10_first/A]
report_slews -digits 9 [get_pins rstb10_final/A]
report_slews -digits 9 [get_pins rstb10_final/Y]
report_slews -digits 9 [get_pins $target]
puts "RSTB_FINAL_PIN_XY_DBU [[$final findITerm Y] getAvgXY]"
puts "RSTB_MACRO_PIN_XY_DBU [$target_iterm getAvgXY]"
report_net rstb10_out
puts RSTB_LOCAL_END
