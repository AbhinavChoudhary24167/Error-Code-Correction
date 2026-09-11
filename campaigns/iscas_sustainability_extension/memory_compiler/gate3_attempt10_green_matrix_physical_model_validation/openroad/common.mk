ATTEMPT10_DIR = /work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation
ATTEMPT09_DIR = /work/campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure

# All implementation controls are inherited verbatim from Attempt09.  The only
# experimental variable is ATTEMPT10_MODEL, which selects an isolated macro
# Liberty view.  Source RTL, SDC, LEF, GDS, placement and repair Tcl remain
# frozen Attempt09 inputs.
include $(ATTEMPT09_DIR)/openroad/common.mk

