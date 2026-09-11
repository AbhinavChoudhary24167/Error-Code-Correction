export DESIGN_NAME = u0_matched_sram_top
include /repo/campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation/orfs/common.mk

export VERILOG_FILES = \
  $(MACRO_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.v \
  $(CAMPAIGN_DIR)/validation/rtl/matched_memory_tops.sv
export SYNTH_BLACKBOXES = sram22_256x64m4w8
export ADDITIONAL_LEFS = $(MACRO_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.lef
export ADDITIONAL_LIBS = $(MACRO_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib
export ADDITIONAL_GDS = $(MACRO_DIR)/raw/derived_gds/sram22_256x64m4w8.gds
export DIE_AREA = 0 0 1000 470
export CORE_AREA = 10 10 990 460
export MACRO_PLACEMENT_TCL = $(CAMPAIGN_DIR)/orfs/macro_placement_u0.tcl
