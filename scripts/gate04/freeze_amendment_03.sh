#!/usr/bin/env bash
set -euo pipefail

readonly repo="${1:?usage: freeze_amendment_03.sh REPOSITORY_ROOT}"
readonly evidence="/var/lib/green-ecc-gate04"
readonly policy="$evidence/policy"
readonly amendment="$evidence/amendments/03"
readonly attempt="$evidence/runs/secded-comb-10ns-seed11-attempt2"

if [[ "$(id -u)" != "0" ]]; then echo "Run as root inside Ubuntu WSL2." >&2; exit 2; fi
test -d "$policy" -a -d "$evidence/amendments/01" -a -d "$evidence/amendments/02"
test -f "$attempt/run-metadata.json"
grep -q '"exit_status": 93' "$attempt/run-metadata.json"
test ! -e "$amendment"
for relative in \
  contract_v1.json candidate_catalog_v1.json rtl/gate04_boundaries.sv configs/gate04.sdc \
  configs/secded_comb.mk configs/secded_pipe.mk configs/hsiao.mk configs/bch.mk \
  configs/boundary72.mk configs/boundary78.mk generate_traces.py generate_reliability.py gate04_power.tcl mapped_equivalence.sh; do
  cmp "$repo/scripts/gate04/$relative" "$policy/repo_snapshot/scripts/gate04/$relative"
done
mkdir -p "$amendment"
for name in run_flow.sh run_matrix.sh validate_run.py postprocess.py final_validate.py complete_attempt2_validation_03.sh freeze_amendment_03.sh mapped_equivalence_abc_dsec.sh; do
  cp -a "$repo/scripts/gate04/$name" "$amendment/$name"
done
cp -a "$repo/docs/date2027/rigour_gate_04/POLICY_AMENDMENT_03.md" "$amendment/"
sha256sum "$attempt/run-metadata.json" "$attempt/container.log" "$attempt/raw-artifacts.sha256" > "$amendment/ATTEMPT2_PHYSICAL_REFERENCE.sha256"
sha256sum \
  "$attempt/mapped-equivalence-dsec-test4.log" "$attempt/mapped-equivalence-dsec-test4.gold.aig" "$attempt/mapped-equivalence-dsec-test4.gate.aig" \
  "$attempt/postroute-equivalence-dsec-test1.log" "$attempt/postroute-equivalence-dsec-test1.gold.aig" "$attempt/postroute-equivalence-dsec-test1.gate.aig" \
  > "$amendment/METHOD_QUALIFICATION_REFERENCE.sha256"
python3 -c 'import datetime,json,pathlib; pathlib.Path("'"$amendment"'/AMENDMENT_METADATA.json").write_text(json.dumps({"schema_version":1,"amendment":"03","frozen_at_utc":datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),"reason":"replace nonterminating per-bit SAT schedule with qualified exact ABC dsec and complete attempt2 post-flow analyses","scientific_contract_changed":False,"physical_flow_rerun":False,"adjudicated_run":"secded-comb-10ns-seed11-attempt2","equivalence_legs":["RTL-to-mapped","mapped-to-postroute"],"post_reset_initialization":"explicit zero via zinit -all"},indent=2,sort_keys=True)+"\n",encoding="utf-8")'
(
  cd "$amendment"
  find . -type f ! -name AMENDMENT.sha256 -print0 | sort -z | xargs -0 sha256sum > AMENDMENT.sha256
  sha256sum --check AMENDMENT.sha256 >/dev/null
)
chmod -R a-w "$amendment"
echo "GATE04_AMENDMENT_03_PASS"
