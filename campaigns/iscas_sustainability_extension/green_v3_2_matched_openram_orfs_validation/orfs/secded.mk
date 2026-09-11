export DESIGN_NAME = secded_matched_sram_top
include /repo/campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation/orfs/common.mk

export VERILOG_FILES = \
  /repo/scripts/gate03r/rtl/secded_characterization_tops.sv \
  $(MACRO_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.v \
  $(MACRO_DIR)/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1.v \
  $(CAMPAIGN_DIR)/validation/rtl/matched_memory_tops.sv
export SYNTH_BLACKBOXES = sram22_256x64m4w8 sram22_256x8m8w1
export ADDITIONAL_LEFS = \
  $(MACRO_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.lef \
  $(MACRO_DIR)/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1.lef
export ADDITIONAL_LIBS = \
  $(MACRO_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib \
  $(MACRO_DIR)/source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib
export ADDITIONAL_GDS = \
  $(MACRO_DIR)/raw/derived_gds/sram22_256x64m4w8.gds \
  $(MACRO_DIR)/raw/derived_gds/sram22_256x8m8w1.gds
export DIE_AREA = 0 0 1000 650
export CORE_AREA = 10 10 990 640
export MACRO_PLACEMENT_TCL = $(CAMPAIGN_DIR)/orfs/macro_placement_72.tcl
