# Attempt05 direct vendor-GDS import through the unmodified normal sky130A
# electrical technology, followed by full leaf DRC and extraction.  The import
# options are the pinned OpenRAM 1.2.48 options.  No MAGLEF substitution occurs.

set cell_name $env(TARGET_CELL)
set gds_file $env(TARGET_GDS)

drc off
gds warning default
gds flatglob *_?mos_m*
gds flatglob sky130_fd_bd_sram__sram_sp_cell_fom_serifs
gds flatglob sky130_fd_bd_sram__sram_sp_cell
gds flatglob sky130_fd_bd_sram__openram_sp_cell_opt1_replica_cell
gds flatglob sky130_fd_bd_sram__openram_sp_cell_opt1a_replica_cell
gds flatglob sky130_fd_bd_sram__sram_sp_cell_opt1_ce
gds flatglob sky130_fd_bd_sram__openram_sp_cell_opt1_replica_ce
gds flatglob sky130_fd_bd_sram__openram_sp_cell_opt1a_replica_ce
gds flatglob sky130_fd_bd_sram__sram_sp_wlstrap_ce
gds flatglob sky130_fd_bd_sram__sram_sp_wlstrap_p_ce
gds flatten true
gds ordering true
gds read $gds_file
load $cell_name
cellname delete \(UNNAMED\)
writeall force
select top cell
expand

drc euclidean on
drc check
drc catchup
set reason_pairs [drc listall why]
set rule_total 0
puts "__RULE_CSV_BEGIN__"
puts "rule,count"
for {set i 0} {$i < [llength $reason_pairs]} {incr i 2} {
    set rule [lindex $reason_pairs $i]
    set rectangles [lindex $reason_pairs [expr {$i + 1}]]
    set count [llength $rectangles]
    incr rule_total $count
    set escaped_rule [string map [list \" \"\"] $rule]
    puts "\"$escaped_rule\",$count"
}
puts "__RULE_CSV_END__"
puts "RULE_TOTAL=$rule_total"
puts "COUNT_TOTAL_WITH_HIERARCHICAL_DOUBLE_COUNTING=[drc listall count total]"

extract style ngspice(si)
extract unique all
extract all
select top cell
feedback why
puts "Finished extract"
ext2spice hierarchy on
ext2spice format ngspice
ext2spice cthresh infinite
ext2spice rthresh infinite
ext2spice renumber off
ext2spice scale off
ext2spice blackbox off
ext2spice subcircuit top on
ext2spice global off
ext2spice $cell_name
select top cell
feedback why
puts "Finished ext2spice"
quit -noprompt
