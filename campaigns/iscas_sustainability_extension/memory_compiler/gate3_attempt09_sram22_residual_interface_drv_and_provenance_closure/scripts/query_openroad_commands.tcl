set prior "/work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt08_sram22_slew_provenance_and_drv_closure"

read_liberty /OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty "$prior/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib"
read_liberty "$prior/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib"
read_db "$prior/raw/openroad/work/results/sky130hd/attempt08_e0/seed11/6_final.odb"
read_sdc "$prior/raw/openroad/work/results/sky130hd/attempt08_e0/seed11/6_final.sdc"
read_spef "$prior/raw/openroad/work/results/sky130hd/attempt08_e0/seed11/6_final.spef"

foreach pattern [list *instance* *connect* *disconnect* *net* *placement* *master* *parasitic*] {
  puts "===== HELP $pattern ====="
  help $pattern
}
foreach pattern [list *place_cell* *location* *move*] {
  puts "===== HELP $pattern ====="
  help $pattern
}

set db [ord::get_db]
set block [ord::get_db_block]
puts "DB=$db"
puts "BLOCK=$block"
puts "MASTER_INV16=[$db findMaster sky130_fd_sc_hd__inv_16]"
puts "MASTER_CLKINV16=[$db findMaster sky130_fd_sc_hd__clkinv_16]"
set macro [$block findInst u_protected_memory.u_data]
puts "MACRO_LOC=[$macro getLocation] ORIENT=[$macro getOrient]"
foreach pin_name [list rstb clk] {
  set iterm [$macro findITerm $pin_name]
  puts "MACRO_PIN=$pin_name AVG_XY=[$iterm getAvgXY] NET=[[$iterm getNet] getName]"
}
