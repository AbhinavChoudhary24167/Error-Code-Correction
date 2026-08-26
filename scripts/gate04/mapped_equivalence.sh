#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 6 ]]; then
  echo "usage: mapped_equivalence.sh RUN_ROOT REPOSITORY_SNAPSHOT TOP COMMA_SEPARATED_GOLD_FILES mapped|postroute OUTPUT_LOG" >&2
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
  mapped) netlist_name="1_2_yosys.v" ;;
  postroute) netlist_name="6_final.v" ;;
  *) echo "invalid netlist kind: $netlist_kind" >&2; exit 3 ;;
esac
mapfile -t netlists < <(find "$run_root/results" -type f -name "$netlist_name")
test "${#netlists[@]}" -eq 1
readonly relative_netlist="${netlists[0]#"$run_root"/}"

gold_command=""
IFS=',' read -r -a gold_files <<< "$source_csv"
for source in "${gold_files[@]}"; do
  test -f "$snapshot/$source"
  gold_command+="read_verilog -sv /gate04-repo/$source; "
done

readonly yosys_script="${gold_command}hierarchy -check -top $top; proc; flatten; memory; opt_clean; rename $top gold; design -stash gold_design; design -reset; read_liberty -ignore_miss_func $liberty; read_verilog -sv /gate04-run/$relative_netlist; hierarchy -check -top $top; flatten; proc; opt_clean; rename $top gate; design -stash gate_design; design -reset; design -copy-from gold_design *; design -copy-from gate_design *; equiv_make gold gate equiv; hierarchy -check -top equiv; equiv_simple -undef -seq 8; equiv_induct -undef -seq 8; equiv_status -assert"

docker run --rm --platform linux/amd64 \
  --volume "$run_root:/gate04-run:ro" \
  --volume "$snapshot:/gate04-repo:ro" \
  --entrypoint /bin/bash \
  "$image" \
  -lc "set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; yosys -p '$yosys_script'" \
  > "$output_log" 2>&1
grep -q 'Equivalence successfully proven' "$output_log"
echo "GATE04_EQUIVALENCE_PASS top=$top netlist=$netlist_kind"
