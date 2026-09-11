#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: run_interface_pair_experiments.sh <repository-root>" >&2
  exit 2
fi

repo_root="$1"
rel="campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"
out="$repo_root/$rel/raw/repair_experiments"
image="sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
openroad=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
mkdir -p "$out"

run_one() {
  local design="$1"
  local label="$2"
  local target="$3"
  local cell="$4"
  docker run --rm \
    -e ATTEMPT09_DESIGN="$design" \
    -e ATTEMPT09_TARGET="$target" \
    -e ATTEMPT09_CELL="$cell" \
    -v "$repo_root:/work" \
    -w /OpenROAD-flow-scripts/flow \
    "$image" "$openroad" -exit "/work/$rel/scripts/interface_pair_experiment.tcl" \
    > "$out/$label.log" 2>&1
}

for strength in 8 12 16; do
  run_one u0 "u0_data_rstb_inv${strength}_pair" u_data/rstb "sky130_fd_sc_hd__inv_${strength}"
  run_one e0 "e0_data_rstb_inv${strength}_pair" u_protected_memory.u_data/rstb "sky130_fd_sc_hd__inv_${strength}"
  run_one e0 "e0_ecc_rstb_inv${strength}_pair" u_protected_memory.u_ecc/rstb "sky130_fd_sc_hd__inv_${strength}"
done

for strength in 8 16; do
  run_one e0 "e0_data_clk_clkinv${strength}_pair" u_protected_memory.u_data/clk "sky130_fd_sc_hd__clkinv_${strength}"
  run_one u0 "u0_data_rstb_clkinv${strength}_pair" u_data/rstb "sky130_fd_sc_hd__clkinv_${strength}"
  run_one e0 "e0_data_rstb_clkinv${strength}_pair" u_protected_memory.u_data/rstb "sky130_fd_sc_hd__clkinv_${strength}"
  run_one e0 "e0_ecc_rstb_clkinv${strength}_pair" u_protected_memory.u_ecc/rstb "sky130_fd_sc_hd__clkinv_${strength}"
done

for cell in nand2_8 nand3_4 nand4_4; do
  run_one u0 "u0_data_rstb_${cell}_pair" u_data/rstb "sky130_fd_sc_hd__${cell}"
  run_one e0 "e0_data_rstb_${cell}_pair" u_protected_memory.u_data/rstb "sky130_fd_sc_hd__${cell}"
done

for cell in bufinv_16 lpflow_clkinvkapwr_16; do
  run_one u0 "u0_data_rstb_${cell}_pair" u_data/rstb "sky130_fd_sc_hd__${cell}"
  run_one e0 "e0_data_rstb_${cell}_pair" u_protected_memory.u_data/rstb "sky130_fd_sc_hd__${cell}"
done
