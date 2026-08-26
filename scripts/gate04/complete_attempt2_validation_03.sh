#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" != "0" ]]; then
  echo "Run as root inside Ubuntu WSL2." >&2
  exit 2
fi
readonly evidence="/var/lib/green-ecc-gate04"
readonly policy="$evidence/policy"
readonly snapshot="$policy/repo_snapshot"
readonly amendment="$evidence/amendments/03"
readonly run_root="$evidence/runs/secded-comb-10ns-seed11-attempt2"
readonly top="gate04_secded_comb_72_64"
readonly image="openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
readonly config="/gate04-repo/scripts/gate04/configs/secded_comb.mk"
readonly gold_files="scripts/gate03r/rtl/secded_characterization_tops.sv,scripts/gate04/rtl/gate04_boundaries.sv"

(cd "$policy" && sha256sum --check frozen-bundle.sha256 >/dev/null)
(cd "$amendment" && sha256sum --check AMENDMENT.sha256 >/dev/null)
(cd "$run_root" && sha256sum --check raw-artifacts.sha256 >/dev/null)
grep -q '"exit_status": 93' "$run_root/run-metadata.json"
test ! -e "$run_root/amendment03-validation-metadata.json"
test ! -e "$run_root/mapped-equivalence-dsec.log"
test ! -e "$run_root/postroute-equivalence-dsec.log"
test ! -e "$run_root/power"
readonly results="$run_root/results/sky130hd/$top/base"
for artifact in 1_synth.odb 2_floorplan.odb 3_place.odb 4_cts.odb 5_route.odb 6_final.odb 6_final.v 6_final.sdc 6_final.def 6_final.gds 6_final.spef; do
  test -s "$results/$artifact"
done
if grep -Eq '^[[:space:]]*(\$_|\\\$)' "$results/6_final.v"; then
  echo "generic cell type remains" >&2
  exit 93
fi

bash "$amendment/mapped_equivalence_abc_dsec.sh" \
  "$run_root" "$snapshot" "$top" "$gold_files" mapped "$run_root/mapped-equivalence-dsec.log"
bash "$amendment/mapped_equivalence_abc_dsec.sh" \
  "$run_root" "$snapshot" "$top" "$gold_files" postroute "$run_root/postroute-equivalence-dsec.log"

mkdir "$run_root/power"
readonly trace_specs="conventional_secded-no_error|/gate04-policy/traces/conventional_secded-10ns-no_error.vcd.gz,conventional_secded-single_error|/gate04-policy/traces/conventional_secded-10ns-single_error.vcd.gz,conventional_secded-double_error|/gate04-policy/traces/conventional_secded-10ns-double_error.vcd.gz"
docker run --rm --platform linux/amd64 \
  --volume "$run_root:/gate04-run" \
  --volume "$snapshot:/gate04-repo:ro" \
  --volume "$policy:/gate04-policy:ro" \
  --entrypoint /bin/bash \
  "$image" \
  -lc "set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; export LEC_CHECK=0 NUM_CORES=1 WORK_HOME=/gate04-run CLOCK_PERIOD=10.0 GPL_RANDOM_SEED=11 GRT_SEED=11 OR_SEED=11 GATE04_POWER_DIR=/gate04-run/power GATE04_TRACE_SPECS='$trace_specs'; cd /OpenROAD-flow-scripts/flow; make ABC_CLOCK_PERIOD_IN_PS=10000 DESIGN_CONFIG=$config RUN_SCRIPT=/gate04-repo/scripts/gate04/gate04_power.tcl RUN_LOG_NAME_STEM=gate04_power run" \
  > "$run_root/power-container.log" 2>&1
grep -q 'GATE04_POWER_PASS' "$run_root/power-container.log"

python3 "$amendment/validate_run.py" \
  --run-root "$run_root" \
  --implementation-id secded-rtl-combinational-72-64-v1 \
  --top "$top" --n 72 --clock-ns 10.0 \
  > "$run_root/run-validation.log" 2>&1
grep -q '"status": "PASS"' "$run_root/run-validation.json"
python3 -c 'import datetime,json,pathlib; pathlib.Path("'"$run_root"'/amendment03-validation-metadata.json").write_text(json.dumps({"schema_version":1,"status":"PASS","amendment":"03","completed_at_utc":datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),"original_runner_exit_status":93,"physical_flow_reused_without_rerun":True,"rtl_to_mapped_dsec":"PASS","mapped_to_postroute_dsec":"PASS","rtl_to_postroute_by_transitivity":"PASS","activity_power":"PASS","run_validation":"PASS"},indent=2,sort_keys=True)+"\n",encoding="utf-8")'
(
  cd "$run_root"
  find . -type f ! -name raw-artifacts-amendment03.sha256 -print0 | sort -z | xargs -0 sha256sum > raw-artifacts-amendment03.sha256
)
echo "GATE04_ATTEMPT2_AMENDMENT03_PASS"
