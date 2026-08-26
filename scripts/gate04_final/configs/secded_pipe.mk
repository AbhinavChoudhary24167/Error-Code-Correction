export DESIGN_NAME = gate04_secded_pipe_72_64
export PLATFORM = sky130hd
export VERILOG_FILES = \
  /gate04-repo/asic/rtl/secded/secded_pipelined_72_64_v1.sv \
  /gate04-repo/scripts/gate03r/rtl/secded_characterization_tops.sv \
  /gate04-repo/scripts/gate04/rtl/gate04_boundaries.sv
export SDC_FILE = /gate04-repo/scripts/gate04_final/configs/ecc.sdc
export ADDER_MAP_FILE :=
export CORE_UTILIZATION = 35
export CORE_ASPECT_RATIO = 1
export CORE_MARGIN = 10
export PLACE_DENSITY = 0.55
