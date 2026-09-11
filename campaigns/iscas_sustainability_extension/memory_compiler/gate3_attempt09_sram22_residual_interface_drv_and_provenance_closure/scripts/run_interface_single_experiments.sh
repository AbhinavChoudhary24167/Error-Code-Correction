#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: run_interface_single_experiments.sh <repository-root>" >&2
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
  local inputs="$5"
  local output="$6"
  docker run --rm \
    -e ATTEMPT09_DESIGN="$design" \
    -e ATTEMPT09_TARGET="$target" \
    -e ATTEMPT09_CELL="$cell" \
    -e ATTEMPT09_INPUTS="$inputs" \
    -e ATTEMPT09_OUTPUT="$output" \
    -v "$repo_root:/work" \
    -w /OpenROAD-flow-scripts/flow \
    "$image" "$openroad" -exit "/work/$rel/scripts/interface_single_experiment.tcl" \
    > "$out/$label.log" 2>&1
}

for design_target in \
  'u0|u_data/rstb|u0_data_rstb' \
  'e0|u_protected_memory.u_data/rstb|e0_data_rstb'; do
  IFS='|' read -r design target label <<< "$design_target"
  run_one "$design" "${label}_lpflow_clkbufkapwr16" "$target" sky130_fd_sc_hd__lpflow_clkbufkapwr_16 A X
  run_one "$design" "${label}_mux2_8" "$target" sky130_fd_sc_hd__mux2_8 A0,A1,S X
  run_one "$design" "${label}_and4_4" "$target" sky130_fd_sc_hd__and4_4 A,B,C,D X
  run_one "$design" "${label}_or4_4" "$target" sky130_fd_sc_hd__or4_4 A,B,C,D X
done
