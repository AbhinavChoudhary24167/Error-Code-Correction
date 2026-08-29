export DESIGN_NAME = gate04_rev2_hsiao_72_64
export PLATFORM = sky130hd
export VERILOG_FILES = \
  /breadth-repo/green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv \
  /breadth-repo/green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv \
  /breadth-repo/green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v2_algorithmic_decoder.sv \
  /breadth-repo/scripts/revision2/rtl/rev2_hsiao_boundary.sv
export SDC_FILE = /breadth-repo/campaigns/date_2027_breadth_remediation/configs/ecc.sdc
export ADDER_MAP_FILE :=
export CORE_UTILIZATION = 35
export CORE_ASPECT_RATIO = 1
export CORE_MARGIN = 10
export PLACE_DENSITY = 0.55
