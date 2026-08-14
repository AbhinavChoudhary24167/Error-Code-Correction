export DESIGN_NAME = gate03e_secded_pipelined_boundary
export PLATFORM = sky130hd
export VERILOG_FILES = \
  /gate03e-repo/asic/rtl/secded/secded_pipelined_72_64_v1.sv \
  /gate03e-repo/scripts/gate03e/mapping/independent_channel_boundaries.sv
export SDC_FILE = /gate03e-repo/scripts/gate03e/mapping/pipelined.sdc
export ADDER_MAP_FILE :=
