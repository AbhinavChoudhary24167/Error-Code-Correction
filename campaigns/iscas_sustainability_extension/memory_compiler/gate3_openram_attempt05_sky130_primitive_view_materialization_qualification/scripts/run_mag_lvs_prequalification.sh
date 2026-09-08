#!/usr/bin/env bash

set -euo pipefail

attempt_root="${ATTEMPT04_ROOT:-/attempt}"
campaign_root="${ATTEMPT05_ROOT:-/campaign}"
openram_root="${attempt_root}/source/OpenRAM"
tech_root="${openram_root}/technology/sky130"
result_root="${campaign_root}/raw/leaf_prequalification"
cell_manifest="${campaign_root}/scripts/leaf_cells.json"

export OPENRAM_HOME="${openram_root}/compiler"
export OPENRAM_TECH="${openram_root}/technology"
export PDK_ROOT="${attempt_root}/pdk"

mapfile -t cells < <(python3 -c 'import json,sys; print("\n".join(x["cell"] for x in json.load(open(sys.argv[1]))))' "${cell_manifest}")

for cell in "${cells[@]}"; do
    view_root="${result_root}/${cell}/lvs_mag"
    physical_source="${tech_root}/mag_lib/${cell}.mag"
    schematic_source="${tech_root}/lvs_lib/${cell}.sp"
    mkdir -p "${view_root}"
    if [[ ! -f "${physical_source}" || ! -f "${schematic_source}" ]]; then
        printf 'FULL_MAG=%s\nSCHEMATIC=%s\n' \
            "$(test -f "${physical_source}" && echo AVAILABLE || echo NOT_AVAILABLE)" \
            "$(test -f "${schematic_source}" && echo AVAILABLE || echo NOT_AVAILABLE)" \
            > "${view_root}/availability.log"
        continue
    fi
    cp "${physical_source}" "${view_root}/${cell}.mag"
    cp "${schematic_source}" "${view_root}/${cell}.schematic.spice"
    cp "${tech_root}/tech/.magicrc" "${view_root}/.magicrc"
    cp "${attempt_root}/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl" "${view_root}/setup.tcl"
    (
        cd "${view_root}"
        TARGET_CELL="${cell}" magic -dnull -noconsole \
            < "${campaign_root}/diagnostics/extract_leaf.tcl" \
            > extraction.log 2>&1
        netgen -batch lvs \
            "${cell}.spice ${cell}" \
            "${cell}.schematic.spice ${cell}" \
            setup.tcl lvs.report -full -json \
            > netgen.log 2>&1 || true
    )
done

printf 'Attempt05 full-MAG LVS prequalification complete: %s cells\n' "${#cells[@]}"
