# Gate-3 attempt03 diagnostic instrumentation.
#
# This script reads an already generated Magic cell and the unmodified pinned
# SKY130A DRC deck.  It does not waive, edit, or suppress any rule.

set cell_name $env(DRC_CELL)
load $cell_name -dereference
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
