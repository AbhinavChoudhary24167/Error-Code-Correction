export DESIGN_NICKNAME = attempt06_u0
export DESIGN_NAME = u0_sram22_top
export PLATFORM = sky130hd

ATTEMPT06_DIR = /work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt06_replacement_sram_backend_qualification

export VERILOG_FILES = \
  $(ATTEMPT06_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.v \
  $(ATTEMPT06_DIR)/rtl/unprotected_sram_256x64_sram22.sv
export SYNTH_BLACKBOXES = sram22_256x64m4w8

export SDC_FILE = $(ATTEMPT06_DIR)/openroad/u0/constraint.sdc
export ADDITIONAL_LEFS = $(ATTEMPT06_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.lef
export ADDITIONAL_LIBS = $(ATTEMPT06_DIR)/source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib
export ADDITIONAL_GDS = $(ATTEMPT06_DIR)/raw/derived_gds/sram22_256x64m4w8.gds

export DIE_AREA = 0 0 900 500
export CORE_AREA = 10 10 890 490
export PLACE_DENSITY = 0.35
export MACRO_PLACE_HALO = 10 10
export PDN_TCL = $(ATTEMPT06_DIR)/openroad/pdn_sram22.tcl
export PRE_RESIZE_TCL = $(ATTEMPT06_DIR)/openroad/pre_resize_sram22.tcl
export GPL_RANDOM_SEED = 1
export SKIP_INCREMENTAL_REPAIR = 1
export SKIP_GATE_CLONING = 1
export LEC_CHECK = 0
export REMOVE_CELLS_FOR_LEC = sky130_fd_sc_hd__tapvpwrvgnd*
