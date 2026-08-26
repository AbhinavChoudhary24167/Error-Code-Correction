#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" != "0" ]]; then
  echo "Run as root inside Ubuntu WSL2." >&2
  exit 2
fi
if [[ $# != 1 ]]; then
  echo "usage: complete_validation_04.sh RUN_ID" >&2
  exit 3
fi
readonly run_id="$1"
readonly evidence="/var/lib/green-ecc-gate04"
readonly policy="$evidence/policy"
readonly amendment="$evidence/amendments/04"
readonly run_root="$evidence/runs/$run_id"

(cd "$policy" && sha256sum --check frozen-bundle.sha256 >/dev/null)
(cd "$amendment" && sha256sum --check AMENDMENT.sha256 >/dev/null)
(cd "$run_root" && sha256sum --check raw-artifacts.sha256 >/dev/null)
grep -q '"exit_status": 99' "$run_root/run-metadata.json"
test ! -e "$run_root/amendment04-validation-metadata.json"
test ! -e "$run_root/run-validation.json"
grep -q 'RUN VALIDATION FAIL: no generic Yosys cell remains: None' "$run_root/run-validation.log"
grep -q 'Networks are equivalent.' "$run_root/mapped-equivalence-dsec.log"
grep -q 'Networks are equivalent.' "$run_root/postroute-equivalence-dsec.log"
grep -q 'GATE04_POWER_PASS' "$run_root/power-container.log"

implementation_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["implementation_id"])' "$run_root/run-metadata.json")"
top="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["design_top"])' "$run_root/run-metadata.json")"
n="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["n"])' "$run_root/run-metadata.json")"
clock="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["clock_period_ns"])' "$run_root/run-metadata.json")"
python3 "$amendment/validate_run.py" \
  --run-root "$run_root" --implementation-id "$implementation_id" --top "$top" --n "$n" --clock-ns "$clock" \
  > "$run_root/run-validation-amendment04.log" 2>&1
grep -q '"status": "PASS"' "$run_root/run-validation.json"
python3 -c 'import datetime,json,pathlib; pathlib.Path("'"$run_root"'/amendment04-validation-metadata.json").write_text(json.dumps({"schema_version":1,"status":"PASS","amendment":"04","completed_at_utc":datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),"original_runner_exit_status":99,"physical_flow_reused_without_rerun":True,"equivalence_reused_without_rerun":True,"activity_power_reused_without_rerun":True,"line_local_generic_cell_validation":"PASS","run_validation":"PASS"},indent=2,sort_keys=True)+"\n",encoding="utf-8")'
(
  cd "$run_root"
  find . -type f ! -name raw-artifacts-amendment04.sha256 -print0 | sort -z | xargs -0 sha256sum > raw-artifacts-amendment04.sha256
)
echo "GATE04_AMENDMENT04_VALIDATION_PASS run=$run_id"
