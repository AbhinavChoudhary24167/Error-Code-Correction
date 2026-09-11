#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: run_cell_swap_experiments.sh <repository-root>" >&2
  exit 2
fi

repo_root="$1"
rel="campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt08_sram22_slew_provenance_and_drv_closure"
out="$repo_root/$rel/raw/repair_experiments"
image="sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
openroad=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
mkdir -p "$out"

run_one() {
  local label="$1"
  local instance="$2"
  local master="$3"
  local pin="$4"
  docker run --rm \
    -e ATTEMPT08_INSTANCE="$instance" \
    -e ATTEMPT08_MASTER="$master" \
    -e ATTEMPT08_PIN="$pin" \
    -v "$repo_root:/work" \
    -w /OpenROAD-flow-scripts/flow \
    "$image" "$openroad" -exit "/work/$rel/scripts/cell_swap_experiment.tcl" \
    > "$out/$label.log" 2>&1
}

run_one class_a_xnor2_2 _513_ sky130_fd_sc_hd__xnor2_2 _513_/Y
run_one data_din56_buf8 place757 sky130_fd_sc_hd__buf_8 'u_protected_memory.u_data/din[56]'
run_one data_din57_buf8 place755 sky130_fd_sc_hd__buf_8 'u_protected_memory.u_data/din[57]'
run_one data_rstb_clkbuf16 hold824 sky130_fd_sc_hd__clkbuf_16 u_protected_memory.u_data/rstb
run_one ecc_rstb_bufbuf16 wire634 sky130_fd_sc_hd__bufbuf_16 u_protected_memory.u_ecc/rstb
run_one ecc_rstb_clkbuf16 wire634 sky130_fd_sc_hd__clkbuf_16 u_protected_memory.u_ecc/rstb
run_one data_clk_buf16 clkbuf_1_1__f_clk sky130_fd_sc_hd__buf_16 u_protected_memory.u_data/clk
run_one data_clk_bufbuf16 clkbuf_1_1__f_clk sky130_fd_sc_hd__bufbuf_16 u_protected_memory.u_data/clk
