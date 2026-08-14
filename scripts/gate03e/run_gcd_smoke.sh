#!/usr/bin/env bash
set -euo pipefail

readonly image="openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
readonly evidence_root="/var/lib/green-ecc-gate03e"

if [[ "$(id -u)" != "0" ]]; then
  echo "Run as root inside Ubuntu WSL2." >&2
  exit 2
fi
if [[ $# != 1 || ( "$1" != "1" && "$1" != "2" ) ]]; then
  echo "Usage: $0 1|2" >&2
  exit 3
fi

if [[ "$1" == "1" ]]; then
  readonly run_label="gcd-run-01"
  readonly container_root="/gate03e-run-01"
else
  readonly run_label="gcd-run-02"
  readonly container_root="/gate03e-run-02"
fi
readonly host_root="$evidence_root/runs/$run_label"

(cd "$evidence_root/policy" && sha256sum --check frozen-bundle.sha256)
test -f "$evidence_root/commands/command-manifest.json"
test ! -e "$host_root"
mkdir "$host_root"

printf '%s\n' \
  'source /OpenROAD-flow-scripts/env.sh' \
  'export LEC_CHECK=0' \
  "export WORK_HOME=$container_root" \
  'cd /OpenROAD-flow-scripts/flow' \
  'make DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk' \
  > "$host_root/run-command.txt"

start_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
set +e
docker run --rm --platform linux/amd64 \
  --volume "$host_root:$container_root" \
  --entrypoint /bin/bash \
  "$image" \
  -lc "set -euo pipefail; cd /OpenROAD-flow-scripts; source ./env.sh; export LEC_CHECK=0; export WORK_HOME=$container_root; cd flow; make DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk" \
  > "$host_root/container.log" 2>&1
status=$?
set -e
end_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

printf '{\n  "schema_version": 1,\n  "run_label": "%s",\n  "container_root": "%s",\n  "start_time": "%s",\n  "end_time": "%s",\n  "exit_status": %d\n}\n' \
  "gcd-smoke" "$container_root" "$start_utc" "$end_utc" "$status" \
  > "$host_root/run-metadata.json"

if [[ $status != 0 ]]; then
  echo "$run_label failed with exit status $status; raw output retained at $host_root" >&2
  exit "$status"
fi

readonly results="$host_root/results/sky130hd/gcd/base"
readonly logs="$host_root/logs/sky130hd/gcd/base"
readonly reports="$host_root/reports/sky130hd/gcd/base"
test -d "$results" -a -d "$logs" -a -d "$reports"
for artifact in \
  1_synth.odb 2_floorplan.odb 3_place.odb 4_cts.odb 5_route.odb \
  6_final.odb 6_final.v 6_final.sdc 6_final.def 6_final.gds 6_final.spef; do
  test -s "$results/$artifact"
done
for stage in 1 2 3 4 5 6; do
  find "$logs" -maxdepth 1 -type f -name "${stage}_*" -print -quit | grep -q .
done
test -s "$logs/6_report.log"
echo "GATE03E_GCD_SMOKE_PASS $run_label"
