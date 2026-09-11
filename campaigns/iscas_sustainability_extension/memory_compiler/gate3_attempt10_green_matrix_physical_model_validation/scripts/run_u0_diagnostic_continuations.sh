#!/usr/bin/env bash
set -u
if [[ $# -ne 1 ]]; then echo "usage: run_u0_diagnostic_continuations.sh <repository-root>" >&2; exit 2; fi
repo_root="$1"
campaign_rel="campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation"
external="/var/tmp/green-ecc-attempt10/orfs"
work_home="/attempt10-work"
image="sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
config="/work/$campaign_rel/openroad/u0/config.mk"
hook="/work/$campaign_rel/openroad/diagnostic_continue_rsz0090.tcl"
mkdir -p "$external/driver_logs"
for model in CORRECTED PIN_SPECIFIC_OR_NO_GLOBAL_COUNTERFACTUAL; do
  for seed in 11 13 17 19 23; do
    nickname="attempt10_${model}_u0_CONTINUATION"
    variant="seed${seed}"
    result="$external/results/sky130hd/$nickname/$variant"
    log="$external/driver_logs/${model}_u0_CONTINUATION_seed${seed}.log"
    if [[ -s "$result/6_final.odb" ]]; then echo "ATTEMPT10_CONTINUATION_SKIP $model $seed"; continue; fi
    echo "ATTEMPT10_CONTINUATION_BEGIN model=$model seed=$seed"
    docker run --rm --volume "$repo_root:/work:ro" --volume "$external:$work_home" --workdir /OpenROAD-flow-scripts/flow "$image" \
      make DESIGN_CONFIG="$config" WORK_HOME="$work_home" FLOW_VARIANT="$variant" ATTEMPT10_MODEL="$model" ATTEMPT10_RUN_SUFFIX="_CONTINUATION" PRE_GLOBAL_PLACE_TCL="$hook" GPL_RANDOM_SEED="$seed" GRT_SEED="$seed" "$work_home/results/sky130hd/$nickname/$variant/3_3_place_gp.odb" > "$log" 2>&1
    rc=$?
    if [[ $rc -eq 0 ]]; then
      cp "$result/3_3_place_gp.odb" "$result/3_4_place_resized.odb"
      docker run --rm --volume "$repo_root:/work:ro" --volume "$external:$work_home" --workdir /OpenROAD-flow-scripts/flow "$image" \
        make DESIGN_CONFIG="$config" WORK_HOME="$work_home" FLOW_VARIANT="$variant" ATTEMPT10_MODEL="$model" ATTEMPT10_RUN_SUFFIX="_CONTINUATION" PRE_GLOBAL_PLACE_TCL="$hook" GPL_RANDOM_SEED="$seed" GRT_SEED="$seed" finish >> "$log" 2>&1
      rc=$?
    fi
    echo "ATTEMPT10_CONTINUATION_END model=$model seed=$seed exit=$rc"
  done
done
