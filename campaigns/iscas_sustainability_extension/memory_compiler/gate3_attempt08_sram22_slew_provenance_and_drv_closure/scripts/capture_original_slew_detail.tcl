if { ![info exists ::env(ATTEMPT08_DESIGN)] } {
  puts stderr "ATTEMPT08_DESIGN must be u0 or e0"
  exit 2
}

set design $::env(ATTEMPT08_DESIGN)
set memory_root "/work/campaigns/iscas_sustainability_extension/memory_compiler"
set prior "$memory_root/gate3_attempt07_sram22_matched_physical_closure"

read_liberty /OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty "$prior/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib"
if { $design == "e0" } {
  read_liberty "$prior/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib"
}

set results "$prior/raw/openroad/work/results/sky130hd/attempt07_${design}/seed11"
read_db "$results/6_final.odb"
read_sdc "$results/6_final.sdc"
read_spef "$results/6_final.spef"

puts "ATTEMPT08_ORIGINAL_SLEW_DETAIL_BEGIN design=$design seed=11"
if { $design == "u0" } {
  foreach pattern [list {u_data/dout[*]} {u_data/rstb}] {
    puts "ATTEMPT08_PATTERN $pattern"
    foreach pin [get_pins $pattern] {
      report_slews -digits 9 $pin
    }
  }
} else {
  foreach pattern [list \
      {u_protected_memory.u_data/dout[*]} \
      {u_protected_memory.u_ecc/dout[*]} \
      {u_protected_memory.u_data/rstb} \
      {u_protected_memory.u_data/clk} \
      {u_protected_memory.u_data/din[56]} \
      {u_protected_memory.u_data/din[57]} \
      {u_protected_memory.u_ecc/rstb} \
      {_513_/Y} {_518_/A} {_540_/A}] {
    puts "ATTEMPT08_PATTERN $pattern"
    foreach pin [get_pins $pattern] {
      report_slews -digits 9 $pin
    }
  }
}
puts "ATTEMPT08_ORIGINAL_SLEW_DETAIL_END design=$design seed=11"
