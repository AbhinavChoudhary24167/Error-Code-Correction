if { ![info exists ::env(ATTEMPT08_DESIGN)] || ![info exists ::env(ATTEMPT08_SEED)] } {
  puts stderr "ATTEMPT08_DESIGN and ATTEMPT08_SEED must be set"
  exit 2
}

set design $::env(ATTEMPT08_DESIGN)
set seed $::env(ATTEMPT08_SEED)
set memory_root "/work/campaigns/iscas_sustainability_extension/memory_compiler"
set prior "$memory_root/gate3_attempt07_sram22_matched_physical_closure"
set stdlib "/OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"

read_liberty $stdlib
read_liberty "$prior/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib"
if { $design == "e0" } {
  read_liberty "$prior/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib"
}

set nickname "attempt07_${design}"
set results "$prior/raw/openroad/work/results/sky130hd/$nickname/seed$seed"
read_db "$results/6_final.odb"
read_sdc "$results/6_final.sdc"
read_spef "$results/6_final.spef"

puts "=== REPORT_CHECK_TYPES ==="
report_check_types -max_slew -violators
puts "=== HELP_SLEW ==="
help *slew*
puts "=== HELP_NET ==="
help *net*
puts "=== HELP_ATTRIBUTE ==="
help *property*
puts "=== HELP_PIN ==="
help get_pins
puts "=== HELP_OBJECT ==="
help *object*
puts "=== HELP_LIB ==="
help *lib_pin*
puts "=== HELP_CAP ==="
help *capacitance*
puts "=== HELP_FANOUT ==="
help *fanout*

if { $design == "e0" } {
  set block [ord::get_db_block]
  puts "=== SUSPECT_NET ==="
  report_net _055_
  puts "=== SUSPECT_PINS ==="
  foreach pin_name [list _513_/Y _518_/A _540_/A u_protected_memory.u_data/rstb u_protected_memory.u_data/clk u_protected_memory.u_data/din\[56\] u_protected_memory.u_data/din\[57\] u_protected_memory.u_ecc/rstb] {
    set pin [get_pins $pin_name]
    puts "PIN=$pin_name"
    report_slews $pin
    set slash [string last "/" $pin_name]
    set inst_name [string range $pin_name 0 [expr {$slash - 1}]]
    set term_name [string range $pin_name [expr {$slash + 1}] end]
    set db_inst [$block findInst $inst_name]
    set db_iterm [$db_inst findITerm $term_name]
    set db_net [$db_iterm getNet]
    set net_name [$db_net getName]
    puts "NET_NAME=$net_name"
    report_net $net_name
    puts "CELL_COLLECTION=[get_cells -of_objects $pin]"
  }
}
