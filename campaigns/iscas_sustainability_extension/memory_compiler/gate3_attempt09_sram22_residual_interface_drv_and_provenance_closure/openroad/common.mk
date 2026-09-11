ATTEMPT09_DIR = /work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure

export PLATFORM = sky130hd
export PLACE_DENSITY = 0.30
export MACRO_PLACE_HALO = 20 20
export MACRO_BLOCKAGE_HALO = 20
export PDN_TCL = $(ATTEMPT09_DIR)/openroad/pdn_sram22.tcl
export PRE_IO_PLACEMENT_TCL = $(ATTEMPT09_DIR)/openroad/pre_io_placement.tcl
export PRE_GLOBAL_ROUTE_TCL = $(ATTEMPT09_DIR)/openroad/pre_global_route_drv_repair.tcl

export ENABLE_PLACE_REPAIR_TIMING = 0
export SKIP_INCREMENTAL_REPAIR = 1
export SKIP_GATE_CLONING = 0
export LEC_CHECK = 0
export REMOVE_CELLS_FOR_LEC = sky130_fd_sc_hd__tapvpwrvgnd*
export DETAILED_METRICS = 1
export GENERATE_ARTIFACTS_ON_FAILURE = 1
