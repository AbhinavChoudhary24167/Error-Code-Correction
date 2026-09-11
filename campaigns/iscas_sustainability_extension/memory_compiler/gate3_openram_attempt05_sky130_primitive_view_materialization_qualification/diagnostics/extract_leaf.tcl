# Attempt05 standalone leaf extraction.  Leaf black-boxing is explicitly off:
# the extracted topology must arise from the supplied physical view.

set cell_name $env(TARGET_CELL)
load $cell_name -dereference
cellname delete \(UNNAMED\)
select top cell
expand
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
