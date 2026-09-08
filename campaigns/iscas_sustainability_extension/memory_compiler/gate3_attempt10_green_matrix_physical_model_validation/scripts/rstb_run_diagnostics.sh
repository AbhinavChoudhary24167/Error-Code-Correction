#!/usr/bin/env bash
set -euo pipefail
repo_root=${1:?Usage: rstb_run_diagnostics.sh repository-root}
campaign=campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation
image=sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e
openroad=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
sta=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta
mkdir -p "$repo_root/$campaign/rstb/raw"
for macro in sram22_256x64m4w8 sram22_256x8m8w1; do
  for family in buf clkbuf inv clkinv; do
    output="$repo_root/$campaign/rstb/raw/zero_${macro}_${family}.log"
    test ! -e "$output" || { echo "Refusing to overwrite $output" >&2; exit 3; }
    docker run --rm --cpus 1 --volume "$repo_root:/work:ro" --workdir /work \
      --env RSTB_MACRO="$macro" --env RSTB_FAMILY="$family" "$image" \
      "$sta" -exit "/work/$campaign/scripts/rstb_zero_wire.tcl" > "$output" 2>&1
  done
done
for design in u0 e0; do
  output="$repo_root/$campaign/rstb/raw/postroute_${design}.log"
  test ! -e "$output" || { echo "Refusing to overwrite $output" >&2; exit 3; }
  docker run --rm --cpus 1 --volume "$repo_root:/work:ro" --workdir /work --env RSTB_DESIGN="$design" \
    "$image" "$openroad" -exit "/work/$campaign/scripts/rstb_postroute.tcl" > "$output" 2>&1
done
