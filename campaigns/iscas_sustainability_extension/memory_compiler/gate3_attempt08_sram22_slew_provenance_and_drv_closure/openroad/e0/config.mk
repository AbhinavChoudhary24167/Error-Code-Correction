export DESIGN_NICKNAME = attempt08_e0
export DESIGN_NAME = e0_sram22_top

include /work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt08_sram22_slew_provenance_and_drv_closure/openroad/common.mk

export VERILOG_FILES = \
  $(ATTEMPT08_DIR)/rtl/hsiao_secded_72_64_v1_encoder.sv \
  $(ATTEMPT08_DIR)/rtl/hsiao_secded_72_64_v1_syndrome.sv \
  $(ATTEMPT08_DIR)/rtl/hsiao_secded_72_64_v2_algorithmic_decoder.sv \
  $(ATTEMPT08_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.v \
  $(ATTEMPT08_DIR)/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1.v \
  $(ATTEMPT08_DIR)/rtl/ecc_sram_256x72_sram22.sv
export SYNTH_BLACKBOXES = sram22_256x64m4w8 sram22_256x8m8w1

export SDC_FILE = $(ATTEMPT08_DIR)/openroad/e0/constraint.sdc
export ADDITIONAL_LEFS = \
  $(ATTEMPT08_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.lef \
  $(ATTEMPT08_DIR)/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1.lef
export ADDITIONAL_LIBS = \
  $(ATTEMPT08_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib \
  $(ATTEMPT08_DIR)/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib
export ADDITIONAL_GDS = \
  $(ATTEMPT08_DIR)/raw/derived_gds/sram22_256x64m4w8.gds \
  $(ATTEMPT08_DIR)/raw/derived_gds/sram22_256x8m8w1.gds

export DIE_AREA = 0 0 1000 650
export CORE_AREA = 10 10 990 640
export MACRO_PLACEMENT_TCL = $(ATTEMPT08_DIR)/openroad/e0/macro_placement.tcl
