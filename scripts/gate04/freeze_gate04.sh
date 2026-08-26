#!/usr/bin/env bash
set -euo pipefail

readonly repo="${1:?usage: freeze_gate04.sh REPOSITORY_ROOT}"
readonly evidence_root="/var/lib/green-ecc-gate04"
readonly orfs_source="/var/lib/green-ecc-gate03e/source/OpenROAD-flow-scripts"
readonly expected_orfs="56496f3980fb6e9e58f10c8aea4a98949c0fe5f2"
readonly image="openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
readonly auth="/mnt/c/Users/Abhinav/.codex/attachments/2b1b4341-4f44-4f84-988c-e3d41cbf7945/pasted-text.txt"

if [[ "$(id -u)" != "0" ]]; then
  echo "Run as root inside Ubuntu WSL2." >&2
  exit 2
fi
test -d "$repo/.git"
test -f "$auth"
test ! -e "$evidence_root"
test "$(git -C "$orfs_source" rev-parse HEAD)" = "$expected_orfs"
test -z "$(git -C "$orfs_source" status --porcelain=v1)"
grep -q '"status": "PASS"' "$repo/docs/date2027/rigour_gate_04/PREFLOW_VALIDATION.json"
grep -q '^GATE04_YOSYS_PREFLIGHT_PASS tops=6$' "$repo/docs/date2027/rigour_gate_04/PREFLOW_YOSYS.log"
grep -q 'tests="5"' "$repo/docs/date2027/rigour_gate_04/PREFLOW_FOCUSED_TESTS.xml"
grep -q 'failures="0"' "$repo/docs/date2027/rigour_gate_04/PREFLOW_FOCUSED_TESTS.xml"
test "$(($(wc -l < "$repo/docs/date2027/rigour_gate_04/RELIABILITY_RESULTS.csv") - 1))" -eq 180

readonly build_root="/var/lib/.green-ecc-gate04-building-$$"
test ! -e "$build_root"
mkdir -p "$build_root/policy/repo_snapshot"
readonly policy="$build_root/policy"
readonly snapshot="$policy/repo_snapshot"

(
  cd "$repo"
  cp --parents -a \
    scripts/gate04 \
    tests/python/test_gate04_contract.py \
    scripts/gate03r/rtl/secded_characterization_tops.sv \
    asic/rtl/secded/secded_pipelined_72_64_v1.sv \
    asic/rtl/bch/bch_78_64_t2_v1.sv \
    green_ecc_physical_simulation/rtl/hsiao_secded_72_64 \
    green_ecc_physical_simulation/registry/implementations/hsiao-generated-combinational-72-64-v1.json \
    green_ecc_physical_simulation/registry/implementations/secded-rtl-pipelined-72-64-v1.json \
    green_ecc_physical_simulation/registry/implementations/shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1.json \
    docs/date2027/rigour_gate_02/CANONICAL_CODE_SPECS.json \
    docs/date2027/rigour_gate_03/ELIGIBLE_IMPLEMENTATION_FREEZE.json \
    docs/date2027/rigour_gate_03r \
    docs/date2027/rigour_gate_04 \
    "$snapshot"
)
cp -a "$auth" "$policy/EXPLICIT_SUPERSEDING_AUTHORIZATION.txt"

mkdir -p "$policy/seed_control_source"
cp -a "$orfs_source/flow/scripts/global_place.tcl" "$policy/seed_control_source/"
cp -a "$orfs_source/flow/scripts/global_place_skip_io.tcl" "$policy/seed_control_source/"
cp -a "$orfs_source/flow/scripts/global_route.tcl" "$policy/seed_control_source/"
cp -a "$orfs_source/flow/scripts/detail_route.tcl" "$policy/seed_control_source/"
cp -a "$orfs_source/flow/scripts/variables.json" "$policy/seed_control_source/"
cp -a "$orfs_source/flow/scripts/variables.yaml" "$policy/seed_control_source/"
grep -RIn -E 'GPL_RANDOM_SEED|GRT_SEED|OR_SEED|random_seed|or_seed' "$policy/seed_control_source" \
  > "$policy/SEED_CONTROL_SOURCE_PROOF.txt"
grep -q 'GPL_RANDOM_SEED' "$policy/SEED_CONTROL_SOURCE_PROOF.txt"
grep -q 'GRT_SEED' "$policy/SEED_CONTROL_SOURCE_PROOF.txt"
grep -q 'OR_SEED' "$policy/SEED_CONTROL_SOURCE_PROOF.txt"

git -C "$orfs_source" rev-parse HEAD > "$policy/ORFS_SOURCE_HEAD.txt"
git -C "$orfs_source" status --porcelain=v1 > "$policy/ORFS_SOURCE_STATUS.txt"
docker image inspect "$image" > "$policy/CONTAINER_IMAGE_INSPECT.json"
grep -q 'sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e' "$policy/CONTAINER_IMAGE_INSPECT.json"

python3 "$snapshot/scripts/gate04/generate_traces.py" \
  --out "$policy/traces" \
  --contract "$snapshot/scripts/gate04/contract_v1.json"

python3 -c 'import datetime,json,pathlib; p=pathlib.Path("'"$policy"'")/"FREEZE_METADATA.json"; p.write_text(json.dumps({"schema_version":1,"frozen_at_utc":datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),"authorization_basis":"SCIENTIFIC_ENVIRONMENT_READY_FORMAL_GATE_FAILED","orfs_commit":"'"$expected_orfs"'","container_image":"'"$image"'","candidate_flows":40,"reference_flows":20,"total_flows":60},indent=2,sort_keys=True)+"\n",encoding="utf-8")'

(
  cd "$policy"
  find . -type f ! -name frozen-bundle.sha256 -print0 | sort -z | xargs -0 sha256sum > frozen-bundle.sha256
  sha256sum --check frozen-bundle.sha256
)
chmod -R a-w "$policy"
mv "$build_root" "$evidence_root"
mkdir "$evidence_root/runs"
echo "GATE04_FREEZE_PASS policy=$evidence_root/policy total_flows=60"
