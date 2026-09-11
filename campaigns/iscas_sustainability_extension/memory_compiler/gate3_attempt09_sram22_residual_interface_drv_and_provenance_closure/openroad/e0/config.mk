export DESIGN_NICKNAME = attempt09_e0
export DESIGN_NAME = e0_sram22_top

include /work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure/openroad/common.mk

export VERILOG_FILES = \
  $(ATTEMPT09_DIR)/rtl/hsiao_secded_72_64_v1_encoder.sv \
  $(ATTEMPT09_DIR)/rtl/hsiao_secded_72_64_v1_syndrome.sv \
  $(ATTEMPT09_DIR)/rtl/hsiao_secded_72_64_v2_algorithmic_decoder.sv \
  $(ATTEMPT09_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.v \
  $(ATTEMPT09_DIR)/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1.v \
  $(ATTEMPT09_DIR)/rtl/ecc_sram_256x72_sram22.sv
export SYNTH_BLACKBOXES = sram22_256x64m4w8 sram22_256x8m8w1

export SDC_FILE = $(ATTEMPT09_DIR)/openroad/e0/constraint.sdc
export ADDITIONAL_LEFS = \
  $(ATTEMPT09_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.lef \
  $(ATTEMPT09_DIR)/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1.lef
export ADDITIONAL_LIBS = \
  $(ATTEMPT09_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib \
  $(ATTEMPT09_DIR)/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib
export ADDITIONAL_GDS = \
  $(ATTEMPT09_DIR)/raw/derived_gds/sram22_256x64m4w8.gds \
  $(ATTEMPT09_DIR)/raw/derived_gds/sram22_256x8m8w1.gds

export DIE_AREA = 0 0 1000 650
export CORE_AREA = 10 10 990 640
export MACRO_PLACEMENT_TCL = $(ATTEMPT09_DIR)/openroad/e0/macro_placement.tcl
