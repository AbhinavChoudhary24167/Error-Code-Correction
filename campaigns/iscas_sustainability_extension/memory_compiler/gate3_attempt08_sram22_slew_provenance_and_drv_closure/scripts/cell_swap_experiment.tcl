if { ![info exists ::env(ATTEMPT08_INSTANCE)] || ![info exists ::env(ATTEMPT08_MASTER)] || ![info exists ::env(ATTEMPT08_PIN)] } {
  puts stderr "ATTEMPT08_INSTANCE, ATTEMPT08_MASTER, and ATTEMPT08_PIN are required"
  exit 2
}

set prior "/work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt07_sram22_matched_physical_closure"
read_liberty /OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty "$prior/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib"
read_liberty "$prior/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib"
set results "$prior/raw/openroad/work/results/sky130hd/attempt07_e0/seed11"
read_db "$results/6_final.odb"
read_sdc "$results/6_final.sdc"
read_spef "$results/6_final.spef"

set block [ord::get_db_block]
set inst [$block findInst $::env(ATTEMPT08_INSTANCE)]
puts "EXPERIMENT instance=[$inst getName] original_master=[[$inst getMaster] getName] candidate_master=$::env(ATTEMPT08_MASTER)"
puts "BEFORE"
report_slews -digits 9 [get_pins $::env(ATTEMPT08_PIN)]
replace_cell $::env(ATTEMPT08_INSTANCE) $::env(ATTEMPT08_MASTER)
puts "AFTER"
report_slews -digits 9 [get_pins $::env(ATTEMPT08_PIN)]
report_check_types -max_slew -violators
