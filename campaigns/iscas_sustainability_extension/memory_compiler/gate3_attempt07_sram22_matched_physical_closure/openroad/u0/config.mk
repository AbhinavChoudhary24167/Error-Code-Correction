export DESIGN_NICKNAME = attempt07_u0
export DESIGN_NAME = u0_sram22_top

include /work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt07_sram22_matched_physical_closure/openroad/common.mk

export VERILOG_FILES = \
  $(ATTEMPT07_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.v \
  $(ATTEMPT07_DIR)/rtl/unprotected_sram_256x64_sram22.sv
export SYNTH_BLACKBOXES = sram22_256x64m4w8

export SDC_FILE = $(ATTEMPT07_DIR)/openroad/u0/constraint.sdc
export ADDITIONAL_LEFS = $(ATTEMPT07_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.lef
export ADDITIONAL_LIBS = $(ATTEMPT07_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib
export ADDITIONAL_GDS = $(ATTEMPT07_DIR)/raw/derived_gds/sram22_256x64m4w8.gds

export DIE_AREA = 0 0 1000 470
export CORE_AREA = 10 10 990 460
export MACRO_PLACEMENT_TCL = $(ATTEMPT07_DIR)/openroad/u0/macro_placement.tcl

