#!/usr/bin/env bash
set -euo pipefail

readonly image="openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
readonly repo="/mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction"
readonly evidence="/var/lib/green-ecc-gate03e/mapping"
readonly mapping_config="/gate03e-repo/scripts/gate03e/mapping"

if [[ "$(id -u)" != "0" ]]; then
  echo "Run as root inside Ubuntu WSL2." >&2
  exit 2
fi
test ! -e "$evidence"
mkdir "$evidence"

jobs=(
  secded-combinational
  secded-pipelined
  bch-encoder
  bch-decoder
)
configs=(
  secded_combinational.mk
  secded_pipelined.mk
  bch_encoder.mk
  bch_decoder.mk
)
designs=(
  gate03e_secded_combinational_boundary
  gate03e_secded_pipelined_boundary
  bch_78_64_t2_v1_encoder
  bch_78_64_t2_v1_decoder
)

for index in 0 1 2 3; do
  job="${jobs[$index]}"
  config="${configs[$index]}"
  design="${designs[$index]}"
  host_root="$evidence/$job"
  test ! -e "$host_root"
  mkdir "$host_root"
  printf '%s\n' \
    'source /OpenROAD-flow-scripts/env.sh' \
    'export LEC_CHECK=0' \
    'export WORK_HOME=/mapping-work' \
    'cd /OpenROAD-flow-scripts/flow' \
    "make synth DESIGN_CONFIG=$mapping_config/$config" \
    > "$host_root/run-command.txt"
  start_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  set +e
  timeout --signal=TERM --kill-after=30s 1200s \
    docker run --rm --platform linux/amd64 \
      --volume "$repo:/gate03e-repo:ro" \
      --volume "$host_root:/mapping-work" \
      --entrypoint /bin/bash \
      "$image" \
      -lc "set -euo pipefail; cd /OpenROAD-flow-scripts; source ./env.sh; export LEC_CHECK=0; export WORK_HOME=/mapping-work; cd flow; make synth DESIGN_CONFIG=$mapping_config/$config" \
      > "$host_root/container.log" 2>&1
  status=$?
  set -e
  end_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '{\n  "schema_version": 1,\n  "job": "%s",\n  "design": "%s",\n  "start_time": "%s",\n  "end_time": "%s",\n  "timeout_seconds": 1200,\n  "exit_status": %d\n}\n' \
    "$job" "$design" "$start_utc" "$end_utc" "$status" \
    > "$host_root/run-metadata.json"
  if [[ "$status" != "0" ]]; then
    echo "Mapping job $job failed with exit status $status; evidence retained." >&2
    exit "$status"
  fi
  result_root="$host_root/results/sky130hd/$design/base"
  log_root="$host_root/logs/sky130hd/$design/base"
  test -s "$result_root/1_2_yosys.v"
  test -s "$result_root/1_synth.odb"
  test -s "$log_root/1_2_yosys.log"
  test -s "$log_root/1_synth.log"
  echo "GATE03E_MAPPING_JOB_PASS $job"
done
