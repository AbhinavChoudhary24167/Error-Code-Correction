export DESIGN_NICKNAME = attempt06_e0
export DESIGN_NAME = e0_sram22_top
export PLATFORM = sky130hd

ATTEMPT06_DIR = /work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt06_replacement_sram_backend_qualification

export VERILOG_FILES = \
  /work/green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv \
  /work/green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv \
  /work/green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v2_algorithmic_decoder.sv \
  $(ATTEMPT06_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.v \
  $(ATTEMPT06_DIR)/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1.v \
  $(ATTEMPT06_DIR)/rtl/ecc_sram_256x72_sram22.sv
export SYNTH_BLACKBOXES = sram22_256x64m4w8 sram22_256x8m8w1

export SDC_FILE = $(ATTEMPT06_DIR)/openroad/e0/constraint.sdc
export ADDITIONAL_LEFS = \
  $(ATTEMPT06_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.lef \
  $(ATTEMPT06_DIR)/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1.lef
export ADDITIONAL_LIBS = \
  $(ATTEMPT06_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib \
  $(ATTEMPT06_DIR)/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib
export ADDITIONAL_GDS = \
  $(ATTEMPT06_DIR)/raw/derived_gds/sram22_256x64m4w8.gds \
  $(ATTEMPT06_DIR)/raw/derived_gds/sram22_256x8m8w1.gds

export DIE_AREA = 0 0 1300 600
export CORE_AREA = 10 10 1290 590
export PLACE_DENSITY = 0.35
export MACRO_PLACE_HALO = 10 10
export PDN_TCL = $(ATTEMPT06_DIR)/openroad/pdn_sram22.tcl
export PRE_RESIZE_TCL = $(ATTEMPT06_DIR)/openroad/pre_resize_sram22.tcl
export GPL_RANDOM_SEED = 1
export SKIP_INCREMENTAL_REPAIR = 1
export SKIP_GATE_CLONING = 1
export LEC_CHECK = 0
export REMOVE_CELLS_FOR_LEC = sky130_fd_sc_hd__tapvpwrvgnd*
