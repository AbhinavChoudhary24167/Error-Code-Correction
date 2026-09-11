#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: run_orfs.sh <u0|e0> <seed> <repository-root>" >&2
  exit 2
fi

design="$1"
seed="$2"
repo_root="$3"
campaign_rel="campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt07_sram22_matched_physical_closure"
campaign_root="$repo_root/$campaign_rel"
work_home="/work/$campaign_rel/raw/openroad/work"
config="/work/$campaign_rel/openroad/$design/config.mk"
driver_dir="$campaign_root/raw/openroad/drivers"
mkdir -p "$driver_dir"

nickname="attempt07_$design"
variant="seed$seed"
result_host="$campaign_root/raw/openroad/work/results/sky130hd/$nickname/$variant"
place_target="$work_home/results/sky130hd/$nickname/$variant/3_3_place_gp.odb"

image="sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
{
  docker run --rm \
    --volume "$repo_root:/work" \
    --workdir /OpenROAD-flow-scripts/flow \
    "$image" \
    make DESIGN_CONFIG="$config" WORK_HOME="$work_home" FLOW_VARIANT="$variant" \
      GPL_RANDOM_SEED="$seed" GRT_SEED="$seed" "$place_target"

  # Common, symmetric policy: Attempt06 proved repair_design cannot meet the
  # immutable 256x64 rstb max-transition constraint with SKY130HD. Preserve
  # timing-driven global placement, carry its database forward for both U0 and
  # E0, and retain every published constraint in final STA.
  cp "$result_host/3_3_place_gp.odb" "$result_host/3_4_place_resized.odb"

  docker run --rm \
    --volume "$repo_root:/work" \
    --workdir /OpenROAD-flow-scripts/flow \
    "$image" \
    make DESIGN_CONFIG="$config" WORK_HOME="$work_home" FLOW_VARIANT="$variant" \
      GPL_RANDOM_SEED="$seed" GRT_SEED="$seed" finish
} 2>&1 | tee "$driver_dir/${design}_seed${seed}.log"
