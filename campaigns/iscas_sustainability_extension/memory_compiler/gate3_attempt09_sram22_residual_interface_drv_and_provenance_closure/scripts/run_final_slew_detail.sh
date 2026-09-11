#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: run_final_slew_detail.sh <repository-root>" >&2
  exit 2
fi

repo_root="$1"
campaign_rel="campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"
campaign_root="$repo_root/$campaign_rel"
image="sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
openroad=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
mkdir -p "$campaign_root/raw/slew_detail"

for design in u0 e0; do
  docker run --rm \
    --volume "$repo_root:/work" \
    --env ATTEMPT09_DESIGN="$design" \
    --workdir /work \
    "$image" \
    "$openroad" -exit "/work/$campaign_rel/scripts/capture_final_slew_detail.tcl" \
    > "$campaign_root/raw/slew_detail/final_${design}.log" 2>&1
done
