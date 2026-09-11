#!/usr/bin/env bash
set -u

if [[ $# -ne 1 ]]; then
  echo "usage: run_liberty_sensitivity.sh <repository-root>" >&2
  exit 2
fi
repo_root="$1"
campaign_rel="campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation"
external_root="/var/tmp/green-ecc-attempt10/orfs"
work_home="/attempt10-work"
image="sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
mkdir -p "$external_root/driver_logs"
status="$external_root/run_status.tsv"
if [[ ! -f "$status" ]]; then
  printf 'model\tdesign\tseed\texit_code\tfinal_odb\n' > "$status"
fi

for model in ORIGINAL CORRECTED PIN_SPECIFIC_OR_NO_GLOBAL_COUNTERFACTUAL; do
  for design in u0 e0; do
    for seed in 11 13 17 19 23; do
      nickname="attempt10_${model}_${design}"
      variant="seed${seed}"
      final_odb="$external_root/results/sky130hd/$nickname/$variant/6_final.odb"
      if [[ -s "$final_odb" ]]; then
        echo "ATTEMPT10_SKIP model=$model design=$design seed=$seed reason=final_exists"
        continue
      fi
      config="/work/$campaign_rel/openroad/$design/config.mk"
      place_target="$work_home/results/sky130hd/$nickname/$variant/3_3_place_gp.odb"
      result_host="$external_root/results/sky130hd/$nickname/$variant"
      log="$external_root/driver_logs/${model}_${design}_seed${seed}.log"
      echo "ATTEMPT10_BEGIN model=$model design=$design seed=$seed"
      docker run --rm --volume "$repo_root:/work:ro" --volume "$external_root:$work_home" \
        --workdir /OpenROAD-flow-scripts/flow "$image" \
        make DESIGN_CONFIG="$config" WORK_HOME="$work_home" FLOW_VARIANT="$variant" \
        ATTEMPT10_MODEL="$model" GPL_RANDOM_SEED="$seed" GRT_SEED="$seed" "$place_target" \
        > "$log" 2>&1
      rc=$?
      if [[ $rc -eq 0 ]]; then
        cp "$result_host/3_3_place_gp.odb" "$result_host/3_4_place_resized.odb"
        docker run --rm --volume "$repo_root:/work:ro" --volume "$external_root:$work_home" \
          --workdir /OpenROAD-flow-scripts/flow "$image" \
          make DESIGN_CONFIG="$config" WORK_HOME="$work_home" FLOW_VARIANT="$variant" \
          ATTEMPT10_MODEL="$model" GPL_RANDOM_SEED="$seed" GRT_SEED="$seed" finish \
          >> "$log" 2>&1
        rc=$?
      fi
      printf '%s\t%s\t%s\t%s\t%s\n' "$model" "$design" "$seed" "$rc" "$final_odb" >> "$status"
      echo "ATTEMPT10_END model=$model design=$design seed=$seed exit=$rc"
    done
  done
done

