#!/usr/bin/env bash

set -euo pipefail

attempt_root="${ATTEMPT04_ROOT:-/attempt}"
campaign_root="${ATTEMPT05_ROOT:-/campaign}"
cell="sky130_sram_1rw_8x16_gate3a03_control_pnand2_0"
source_work="${attempt_root}/evidence/prepatch/work_control_8x16"
source_schematic="${attempt_root}/evidence/prepatch/output_control_8x16/sky130_sram_1rw_8x16_gate3a03_control.lvs.sp"
out="${campaign_root}/raw/generated_pnand2"

export OPENRAM_HOME="${attempt_root}/source/OpenRAM/compiler"
export OPENRAM_TECH="${attempt_root}/source/OpenRAM/technology"
export PDK_ROOT="${attempt_root}/pdk"
export VOLARE_HOME="${attempt_root}/pdk/volare"

if [[ -e "${out}" ]]; then
    echo "refusing to overwrite existing pnand2 evidence: ${out}" >&2
    exit 2
fi

mkdir -p "${out}"
cp "${source_work}/${cell}.mag" "${out}/${cell}.mag"
cp "${source_schematic}" "${out}/control.lvs.sp"
cp "${attempt_root}/source/OpenRAM/technology/sky130/tech/.magicrc" "${out}/.magicrc"
cp "${attempt_root}/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl" "${out}/setup.tcl"

(
    cd "${out}"
    sha256sum "${cell}.mag" control.lvs.sp .magicrc setup.tcl > source_hashes.sha256
    TARGET_CELL="${cell}" magic -dnull -noconsole \
        < "${campaign_root}/diagnostics/drc_leaf.tcl" \
        > drc.log 2>&1
    TARGET_CELL="${cell}" magic -dnull -noconsole \
        < "${campaign_root}/diagnostics/extract_leaf.tcl" \
        > extraction.log 2>&1
    netgen -batch lvs \
        "${cell}.spice ${cell}" \
        "control.lvs.sp ${cell}" \
        setup.tcl lvs.report -full -json \
        > netgen.log 2>&1 || true
)

echo "Attempt05 independent pnand2_0 reproduction complete"
