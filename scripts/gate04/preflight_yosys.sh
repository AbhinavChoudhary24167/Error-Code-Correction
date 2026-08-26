#!/usr/bin/env bash
set -euo pipefail

readonly image="openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
readonly repo="${1:?usage: preflight_yosys.sh REPOSITORY_ROOT OUTPUT_LOG}"
readonly output="${2:?usage: preflight_yosys.sh REPOSITORY_ROOT OUTPUT_LOG}"

test -d "$repo/scripts/gate04"
mkdir -p "$(dirname "$output")"
: > "$output"

check_top() {
  local top="$1"
  shift
  printf 'PREFLIGHT_TOP=%s\n' "$top" >> "$output"
  docker run --rm --platform linux/amd64 \
    --volume "$repo:/gate04-repo:ro" \
    --entrypoint /bin/bash \
    "$image" \
    -lc "set -euo pipefail; source /OpenROAD-flow-scripts/env.sh >/dev/null; yosys -p 'read_verilog -sv $*; hierarchy -check -top $top; proc; check -assert; stat'" \
    >> "$output" 2>&1
}

check_top gate04_secded_comb_72_64 \
  /gate04-repo/scripts/gate03r/rtl/secded_characterization_tops.sv \
  /gate04-repo/scripts/gate04/rtl/gate04_boundaries.sv
check_top gate04_secded_pipe_72_64 \
  /gate04-repo/asic/rtl/secded/secded_pipelined_72_64_v1.sv \
  /gate04-repo/scripts/gate04/rtl/gate04_boundaries.sv
check_top gate04_hsiao_72_64 \
  /gate04-repo/green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv \
  /gate04-repo/green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv \
  /gate04-repo/green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_decoder.sv \
  /gate04-repo/scripts/gate04/rtl/gate04_boundaries.sv
check_top gate04_bch_78_64 \
  /gate04-repo/asic/rtl/bch/bch_78_64_t2_v1.sv \
  /gate04-repo/scripts/gate04/rtl/gate04_boundaries.sv
check_top gate04_boundary_ref_72_64 /gate04-repo/scripts/gate04/rtl/gate04_boundaries.sv
check_top gate04_boundary_ref_78_64 /gate04-repo/scripts/gate04/rtl/gate04_boundaries.sv

printf 'GATE04_YOSYS_PREFLIGHT_PASS tops=6\n' >> "$output"
echo "GATE04_YOSYS_PREFLIGHT_PASS tops=6"
