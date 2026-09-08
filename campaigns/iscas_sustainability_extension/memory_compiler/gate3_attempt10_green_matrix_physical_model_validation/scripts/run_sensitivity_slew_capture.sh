#!/usr/bin/env bash
set -u
if [[ $# -ne 1 ]]; then echo "usage: run_sensitivity_slew_capture.sh <repository-root>" >&2; exit 2; fi
repo_root="$1"
campaign_rel="campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation"
external="/var/tmp/green-ecc-attempt10/orfs"
image="sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
openroad="/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
mkdir -p "$external/slew_detail"
for model in ORIGINAL CORRECTED PIN_SPECIFIC_OR_NO_GLOBAL_COUNTERFACTUAL; do
  for design in u0 e0; do
    for seed in 11 13 17 19 23; do
      if [[ "$design" == "u0" && "$model" != "ORIGINAL" ]]; then
        echo "ATTEMPT10_SLEW_NOT_MEASURED $model $design $seed reason=strict_run_aborted_RSZ-0090"
        continue
      fi
      output="$external/slew_detail/${model}_${design}_seed${seed}.log"
      if [[ -s "$output" ]]; then echo "ATTEMPT10_SLEW_SKIP $model $design $seed"; continue; fi
      echo "ATTEMPT10_SLEW_BEGIN $model $design $seed"
      suffix=""
      docker run --rm --volume "$repo_root:/work:ro" --volume "$external:/attempt10-work:ro" \
        --env ATTEMPT10_MODEL="$model" --env ATTEMPT10_DESIGN="$design" --env ATTEMPT10_SEED="$seed" --env ATTEMPT10_RUN_SUFFIX="$suffix" \
        "$image" "$openroad" -exit "/work/$campaign_rel/scripts/capture_sensitivity_slews.tcl" > "$output" 2>&1
      echo "ATTEMPT10_SLEW_END $model $design $seed exit=$?"
    done
  done
done
