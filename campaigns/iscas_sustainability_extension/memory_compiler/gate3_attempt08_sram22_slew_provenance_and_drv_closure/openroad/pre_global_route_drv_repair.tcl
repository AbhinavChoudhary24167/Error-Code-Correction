# Attempt08 matched repair policy.  Only proven, externally repairable E0
# violations are changed.  Macro constraints and every SRAM22 artifact remain
# untouched.  The same rule is sourced for U0 and E0; U0 has no matching
# standard-cell/integration target.

set attempt08_block [ord::get_db_block]
set attempt08_design [$attempt08_block getName]
set attempt08_replacements 0

proc attempt08_replace_exact { block instance expected replacement reason } {
  set inst [$block findInst $instance]
  if { $inst == "NULL" } {
    utl::error ATTEMPT08 1 "Required repair instance $instance is absent."
  }
  set original [[$inst getMaster] getName]
  if { $original ne $expected } {
    utl::error ATTEMPT08 2 "Repair instance $instance has $original, expected $expected."
  }
  puts "ATTEMPT08_REPAIR instance=$instance original=$original replacement=$replacement reason=$reason"
  replace_cell $instance $replacement
}

proc attempt08_macro_pin_driver { block macro_name pin_name } {
  set macro [$block findInst $macro_name]
  if { $macro == "NULL" } {
    utl::error ATTEMPT08 3 "Required macro $macro_name is absent."
  }
  set sink [$macro findITerm $pin_name]
  if { $sink == "NULL" } {
    utl::error ATTEMPT08 4 "Required macro pin $macro_name/$pin_name is absent."
  }
  set net [$sink getNet]
  set drivers {}
  foreach term [$net getITerms] {
    if { [string equal -nocase [$term getIoType] "OUTPUT"] } {
      lappend drivers [$term getInst]
    }
  }
  if { [llength $drivers] != 1 } {
    utl::error ATTEMPT08 5 "Expected one driver for $macro_name/$pin_name; found [llength $drivers]."
  }
  return [lindex $drivers 0]
}

proc attempt08_upsize_macro_input_buffer { block macro_name pin_name } {
  set driver [attempt08_macro_pin_driver $block $macro_name $pin_name]
  set driver_name [$driver getName]
  set original [[$driver getMaster] getName]
  if { [regexp {^sky130_fd_sc_hd__buf_([124])$} $original] } {
    set replacement sky130_fd_sc_hd__buf_8
    puts "ATTEMPT08_REPAIR instance=$driver_name original=$original replacement=$replacement reason=SRAM_input_external_drive"
    replace_cell $driver_name $replacement
    return 1
  }
  if { $original eq "sky130_fd_sc_hd__buf_8" || $original eq "sky130_fd_sc_hd__buf_16" } {
    puts "ATTEMPT08_REPAIR instance=$driver_name original=$original replacement=NONE reason=already_at_or_above_policy_drive"
    return 0
  }
  utl::error ATTEMPT08 6 "Unsupported driver $original on $macro_name/$pin_name."
}

if { $attempt08_design eq "e0_sram22_top" } {
  attempt08_replace_exact $attempt08_block _513_ \
    sky130_fd_sc_hd__xnor2_1 sky130_fd_sc_hd__xnor2_2 \
    standard_cell_net_max_transition
  incr attempt08_replacements
  incr attempt08_replacements [attempt08_upsize_macro_input_buffer \
    $attempt08_block u_protected_memory.u_data {din[56]}]
  incr attempt08_replacements [attempt08_upsize_macro_input_buffer \
    $attempt08_block u_protected_memory.u_data {din[57]}]
}

if { $attempt08_replacements > 0 } {
  detailed_placement
  check_placement -verbose
}
puts "ATTEMPT08_REPAIR_SUMMARY design=$attempt08_design replacements=$attempt08_replacements constraints_relaxed=0 macro_internals_changed=0"
