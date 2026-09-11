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
    view_root="${result_root}/${cell}/gds_normal"
    gds_source="${tech_root}/gds_lib/${cell}.gds"
    schematic_source="${tech_root}/lvs_lib/${cell}.sp"
    mkdir -p "${view_root}"
    if [[ ! -f "${gds_source}" ]]; then
        printf 'SOURCE_GDS_NOT_AVAILABLE=%s\n' "${gds_source}" > "${view_root}/availability.log"
        continue
    fi
    cp "${gds_source}" "${view_root}/${cell}.source.gds"
    cp "${tech_root}/tech/.magicrc" "${view_root}/.magicrc"
    (
        cd "${view_root}"
        TARGET_CELL="${cell}" TARGET_GDS="${cell}.source.gds" \
            magic -dnull -noconsole \
            < "${campaign_root}/diagnostics/gds_normal_leaf.tcl" \
            > gds_import_drc_extract.log 2>&1
        if [[ -f "${schematic_source}" && -f "${cell}.spice" ]]; then
            cp "${schematic_source}" "${cell}.schematic.spice"
            cp "${attempt_root}/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl" setup.tcl
            netgen -batch lvs \
                "${cell}.spice ${cell}" \
                "${cell}.schematic.spice ${cell}" \
                setup.tcl lvs.report -full -json \
                > netgen.log 2>&1 || true
        else
            printf 'SCHEMATIC_OR_EXTRACTION_NOT_AVAILABLE\n' > availability.log
        fi
    )
done

printf 'Attempt05 direct-GDS prequalification complete: %s cells\n' "${#cells[@]}"
