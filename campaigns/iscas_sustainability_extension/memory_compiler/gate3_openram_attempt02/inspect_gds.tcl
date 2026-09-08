# Read-only Gate-3 attempt-02 GDS inspection under the pinned OpenRAM image.
# Run from the preserved OpenRAM temporary directory so its .magicrc loads
# the exact SKY130A technology revision used for compilation.

drc off
gds warning default
gds read /attempt/evidence/run04_failure/sky130_sram_1rw_72x256_gate3a02.gds
load sky130_sram_1rw_72x256_gate3a02
select top cell
puts "GATE3_GDS_TOP [cellname list self]"
puts "GATE3_GDS_BBOX [box values]"
puts "GATE3_GDS_WIDTH [box width]"
puts "GATE3_GDS_HEIGHT [box height]"
quit -noprompt
