#!/usr/bin/env bash
set -euo pipefail
repo_root=${1:?repository root required}
campaign=campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation
image=sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e
for item in 'u0 u_data/rstb data' 'e0 u_protected_memory.u_data/rstb data' 'e0 u_protected_memory.u_ecc/rstb ecc'; do
  read -r design target kind <<< "$item"
  output="$repo_root/$campaign/rstb/raw/local_${design}_${kind}.log"
  test ! -e "$output" || { echo "Refusing to overwrite $output" >&2; exit 3; }
  docker run --rm --cpus 1 --volume "$repo_root:/work:ro" --workdir /work \
    --env RSTB_DESIGN="$design" --env RSTB_TARGET="$target" "$image" \
    /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit "/work/$campaign/scripts/rstb_local_placement.tcl" > "$output" 2>&1
done
