#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 6 ]]; then
  echo "usage: mapped_equivalence_abc_dsec.sh RUN_ROOT REPOSITORY_SNAPSHOT TOP COMMA_SEPARATED_GOLD_FILES mapped|postroute OUTPUT_LOG" >&2
  exit 2
fi
readonly run_root="$1"
readonly snapshot="$2"
readonly top="$3"
readonly source_csv="$4"
readonly netlist_kind="$5"
readonly output_log="$6"
readonly image="openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
readonly liberty="/OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"

test -d "$run_root/results"
test -d "$snapshot"
case "$netlist_kind" in
  mapped) gate_name="1_2_yosys.v" ;;
  postroute) gate_name="6_final.v" ;;
  *) echo "invalid netlist kind: $netlist_kind" >&2; exit 3 ;;
esac
mapfile -t gate_netlists < <(find "$run_root/results" -type f -name "$gate_name")
test "${#gate_netlists[@]}" -eq 1
readonly relative_gate="${gate_netlists[0]#"$run_root"/}"
mapfile -t mapped_netlists < <(find "$run_root/results" -type f -name "1_2_yosys.v")
test "${#mapped_netlists[@]}" -eq 1
readonly relative_mapped="${mapped_netlists[0]#"$run_root"/}"

readonly proof_tag="$(basename "${output_log%.log}")"
readonly gold_aig="$run_root/$proof_tag.gold.aig"
readonly gate_aig="$run_root/$proof_tag.gate.aig"
test ! -e "$gold_aig"
test ! -e "$gate_aig"

gold_command=""
if [[ "$netlist_kind" = mapped ]]; then
  IFS=',' read -r -a gold_files <<< "$source_csv"
  for source in "${gold_files[@]}"; do
    test -f "$snapshot/$source"
    gold_command+="read_verilog -sv /gate04-repo/$source; "
  done
else
  gold_command="read_liberty -ignore_miss_func $liberty; read_verilog -sv /gate04-run/$relative_mapped; "
fi

readonly prep="hierarchy -check -top $top; proc; flatten; memory; opt; techmap; opt; dffunmap; zinit -all; aigmap; opt_clean"
readonly gold_script="${gold_command}${prep}; write_aiger -symbols /gate04-run/$proof_tag.gold.aig"
readonly gate_script="read_liberty -ignore_miss_func $liberty; read_verilog -sv /gate04-run/$relative_gate; ${prep}; write_aiger -symbols /gate04-run/$proof_tag.gate.aig"

docker run --rm --platform linux/amd64 \
  --volume "$run_root:/gate04-run" \
  --volume "$snapshot:/gate04-repo:ro" \
  --entrypoint /bin/bash \
  "$image" \
  -lc "set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; yosys -p '$gold_script'; yosys -p '$gate_script'; stdbuf -oL yosys-abc -c 'dsec -F 2 -T 120 -r -m -v /gate04-run/$proof_tag.gold.aig /gate04-run/$proof_tag.gate.aig'" \
  > "$output_log" 2>&1

grep -Eq 'Networks are equivalent|Verification of invariant succeeded|proved equivalent' "$output_log"
echo "GATE04_ABC_DSEC_EXACT_EQUIVALENCE_PASS top=$top netlist=$netlist_kind"
