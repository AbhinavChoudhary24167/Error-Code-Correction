# Attempt09 matched external-interface repair policy.
#
# The Attempt08 E0 repairs are preserved. Two further phase-preserving pairs
# are inserted only on targets that closed in constrained candidate analysis:
# an inv_16 pair on the ECC-macro rstb input and a clkinv_16 pair on the
# data-macro clock input. The immutable SRAM22 libraries and SDC are unchanged.

set attempt09_block [ord::get_db_block]
set attempt09_db [ord::get_db]
set attempt09_design [$attempt09_block getName]
set attempt09_replacements 0
set attempt09_insertions 0

proc attempt09_replace_exact { block instance expected replacement reason } {
  set inst [$block findInst $instance]
  if { $inst == "NULL" } {
    utl::error ATTEMPT09 1 "Required repair instance $instance is absent."
  }
  set original [[$inst getMaster] getName]
  if { $original ne $expected } {
    utl::error ATTEMPT09 2 "Repair instance $instance has $original, expected $expected."
  }
  puts "ATTEMPT09_REPAIR instance=$instance original=$original replacement=$replacement reason=$reason"
  replace_cell $instance $replacement
}

proc attempt09_macro_pin_driver { block macro_name pin_name } {
  set macro [$block findInst $macro_name]
  if { $macro == "NULL" } {
    utl::error ATTEMPT09 3 "Required macro $macro_name is absent."
  }
  set sink [$macro findITerm $pin_name]
  if { $sink == "NULL" } {
    utl::error ATTEMPT09 4 "Required macro pin $macro_name/$pin_name is absent."
  }
  set net [$sink getNet]
  set drivers {}
  foreach term [$net getITerms] {
    if { [string equal -nocase [$term getIoType] "OUTPUT"] } {
      lappend drivers [$term getInst]
    }
  }
  if { [llength $drivers] != 1 } {
    utl::error ATTEMPT09 5 "Expected one driver for $macro_name/$pin_name; found [llength $drivers]."
  }
  return [lindex $drivers 0]
}

proc attempt09_upsize_macro_input_buffer { block macro_name pin_name } {
  set driver [attempt09_macro_pin_driver $block $macro_name $pin_name]
  set driver_name [$driver getName]
  set original [[$driver getMaster] getName]
  if { [regexp {^sky130_fd_sc_hd__buf_([124])$} $original] } {
    set replacement sky130_fd_sc_hd__buf_8
    puts "ATTEMPT09_REPAIR instance=$driver_name original=$original replacement=$replacement reason=SRAM_input_external_drive"
    replace_cell $driver_name $replacement
    return 1
  }
  if { $original eq "sky130_fd_sc_hd__buf_8" || $original eq "sky130_fd_sc_hd__buf_16" } {
    puts "ATTEMPT09_REPAIR instance=$driver_name original=$original replacement=NONE reason=already_at_or_above_policy_drive"
    return 0
  }
  utl::error ATTEMPT09 6 "Unsupported driver $original on $macro_name/$pin_name."
}

proc attempt09_insert_phase_preserving_pair { db block macro_name pin_name master_name prefix reason } {
  set macro [$block findInst $macro_name]
  if { $macro == "NULL" } {
    utl::error ATTEMPT09 7 "Required macro $macro_name is absent."
  }
  set sink [$macro findITerm $pin_name]
  if { $sink == "NULL" } {
    utl::error ATTEMPT09 8 "Required macro pin $macro_name/$pin_name is absent."
  }
  set source_net [$sink getNet]
  set source_net_name [$source_net getName]
  set drivers {}
  foreach term [$source_net getITerms] {
    if { [string equal -nocase [$term getIoType] "OUTPUT"] } {
      lappend drivers $term
    }
  }
  if { [llength $drivers] != 1 } {
    utl::error ATTEMPT09 9 "Expected one source on $macro_name/$pin_name; found [llength $drivers]."
  }
  set source_term [lindex $drivers 0]
  set source_inst [$source_term getInst]
  set source_master [[$source_inst getMaster] getName]
  set master [$db findMaster $master_name]
  if { $master == "NULL" } {
    utl::error ATTEMPT09 10 "Required legal master $master_name is absent."
  }

  set mid_net [odb::dbNet_create $block "${prefix}_mid"]
  set out_net [odb::dbNet_create $block "${prefix}_out"]
  set sig_type [$source_net getSigType]
  $mid_net setSigType $sig_type
  $out_net setSigType $sig_type
  set stage1 [odb::dbInst_create $block $master "${prefix}_stage1"]
  set stage2 [odb::dbInst_create $block $master "${prefix}_stage2"]
  [$stage1 findITerm A] connect $source_net
  [$stage1 findITerm Y] connect $mid_net
  [$stage2 findITerm A] connect $mid_net
  [$stage2 findITerm Y] connect $out_net
  $sink disconnect
  $sink connect $out_net

  lassign [$sink getAvgXY] sink_placed sink_x sink_y
  lassign [$source_inst getLocation] source_x source_y
  if { $sink_placed } {
    $stage1 setLocation [expr {$sink_x - 20000}] $source_y
    $stage2 setLocation [expr {$sink_x - 10000}] $source_y
    $stage1 setPlacementStatus PLACED
    $stage2 setPlacementStatus PLACED
  }
  puts "ATTEMPT09_INTERFACE_PAIR target=$macro_name/$pin_name source=$source_net_name driver=[$source_inst getName]/[[$source_term getMTerm] getName] driver_master=$source_master pair_master=$master_name reason=$reason phase_inversions=2 constraints_relaxed=0"
  return 2
}

if { $attempt09_design eq "e0_sram22_top" } {
  attempt09_replace_exact $attempt09_block _513_ \
    sky130_fd_sc_hd__xnor2_1 sky130_fd_sc_hd__xnor2_2 \
    standard_cell_net_max_transition
  incr attempt09_replacements
  incr attempt09_replacements [attempt09_upsize_macro_input_buffer \
    $attempt09_block u_protected_memory.u_data {din[56]}]
  incr attempt09_replacements [attempt09_upsize_macro_input_buffer \
    $attempt09_block u_protected_memory.u_data {din[57]}]
  incr attempt09_insertions [attempt09_insert_phase_preserving_pair \
    $attempt09_db $attempt09_block u_protected_memory.u_ecc rstb \
    sky130_fd_sc_hd__inv_16 attempt09_ecc_rstb \
    minimum_strength_phase_preserving_SRAM_rstb_interface_repair]
  incr attempt09_insertions [attempt09_insert_phase_preserving_pair \
    $attempt09_db $attempt09_block u_protected_memory.u_data clk \
    sky130_fd_sc_hd__clkinv_16 attempt09_data_clk \
    minimum_strength_phase_preserving_SRAM_clock_interface_repair]
  incr attempt09_insertions [attempt09_insert_phase_preserving_pair \
    $attempt09_db $attempt09_block u_protected_memory.u_ecc clk \
    sky130_fd_sc_hd__clkinv_16 attempt09_ecc_clk \
    common_clock_branch_rebalance]
}

if { $attempt09_replacements > 0 || $attempt09_insertions > 0 } {
  global_connect
  detailed_placement
  check_placement -verbose
  estimate_parasitics -placement
  repair_timing -setup_margin 0 -hold_margin 0.025 -repair_tns 100 -match_cell_footprint -verbose
  detailed_placement
  check_placement -verbose
}
puts "ATTEMPT09_REPAIR_SUMMARY design=$attempt09_design replacements=$attempt09_replacements inserted_cells=$attempt09_insertions common_post_interface_hold_repair=1 hold_margin_ns=0.025 constraints_relaxed=0 macro_internals_changed=0 data_macro_rstb_repair_applied=0 data_macro_rstb_feasibility=NO_SINGLE_OUTPUT_SKY130HD_CANDIDATE_CLOSED"
