# Gate-3 attempt04 direct-GDS DRC diagnostic.
#
# This uses the same GDS import options emitted by OpenRAM's unmodified Magic
# extraction script, then runs the unmodified SKY130A DRC deck without copying
# MAGLEF primitive views over the imported GDS hierarchy.

set cell_name $env(DRC_CELL)
set gds_file $env(DRC_GDS)

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
puts "__HIERARCHY_CSV_BEGIN__"
puts "cell,error_tiles"
foreach item [drc listall count] {
    set hierarchy_cell [lindex $item 0]
    set count [lindex $item 1]
    set escaped_cell [string map [list \" \"\"] $hierarchy_cell]
    puts "\"$escaped_cell\",$count"
}
puts "__HIERARCHY_CSV_END__"
puts "COUNT_TOTAL_WITH_HIERARCHICAL_DOUBLE_COUNTING=[drc listall count total]"
quit -noprompt
