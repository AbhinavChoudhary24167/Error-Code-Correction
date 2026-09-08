#!/usr/bin/env bash
set -euo pipefail
repo=/mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction
rel=campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation
image=sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e
design=${1:-u0}
family=${2:-read_dominant}
mkdir -p "$repo/$rel/energy/postroute/$family/${design^^}"
docker run --rm --network none --cpus 1 \
  -v "$repo:/work:ro" -v "$repo/$rel/energy:/output" \
  -e ACTIVITY_DESIGN="$design" -e ACTIVITY_FAMILY="$family" \
  "$image" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit \
  "/work/$rel/scripts/activity_postroute_power.tcl" \
  > "$repo/$rel/energy/postroute/$family/${design^^}/openroad.log" 2>&1
