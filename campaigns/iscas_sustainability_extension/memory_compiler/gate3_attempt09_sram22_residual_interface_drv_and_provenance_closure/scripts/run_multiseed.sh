#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: run_multiseed.sh <repository-root>" >&2
  exit 2
fi

repo_root="$1"
rel="campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"
runner="$repo_root/$rel/scripts/run_orfs.sh"

for design in u0 e0; do
  for seed in 11 13 17 19 23; do
    final_odb="$repo_root/$rel/raw/openroad/work/results/sky130hd/attempt09_${design}/seed${seed}/6_final.odb"
    if [[ -s "$final_odb" ]]; then
      echo "ATTEMPT09_SKIP_COMPLETED design=$design seed=$seed final_odb=$final_odb"
      continue
    fi
    echo "ATTEMPT09_RUN design=$design seed=$seed"
    bash "$runner" "$design" "$seed" "$repo_root"
  done
done
