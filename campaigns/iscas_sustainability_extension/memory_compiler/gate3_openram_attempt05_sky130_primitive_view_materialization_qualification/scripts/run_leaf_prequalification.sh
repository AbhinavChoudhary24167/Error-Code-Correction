#!/usr/bin/env bash

set -euo pipefail

attempt_root="${ATTEMPT04_ROOT:-/attempt}"
campaign_root="${ATTEMPT05_ROOT:-/campaign}"
openram_root="${attempt_root}/source/OpenRAM"
tech_root="${openram_root}/technology/sky130"
result_root="${campaign_root}/raw/leaf_prequalification"
tool_root="${campaign_root}/raw/tool_configuration"
cell_manifest="${campaign_root}/scripts/leaf_cells.json"

mkdir -p "${result_root}" "${tool_root}"
cp "${tech_root}/tech/.magicrc" "${tool_root}/openram.magicrc"
cp "${attempt_root}/pdk/sky130A/libs.tech/magic/sky130A.tech" "${tool_root}/sky130A.tech"
cp "${attempt_root}/pdk/sky130A/libs.tech/magic/sky130A-GDS.tech" "${tool_root}/sky130A-GDS.tech"
cp "${attempt_root}/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl" "${tool_root}/sky130A_setup.tcl"
cp "${tech_root}/tech/tech.py" "${tool_root}/openram_sky130_tech.py"

export OPENRAM_HOME="${openram_root}/compiler"
export OPENRAM_TECH="${openram_root}/technology"
export PDK_ROOT="${attempt_root}/pdk"

mapfile -t cells < <(python3 -c 'import json,sys; print("\n".join(x["cell"] for x in json.load(open(sys.argv[1]))))' "${cell_manifest}")

for cell in "${cells[@]}"; do
    for view in maglef mag; do
        view_source="${tech_root}/${view}_lib/${cell}.mag"
        view_root="${result_root}/${cell}/${view}"
        mkdir -p "${view_root}"
        if [[ ! -f "${view_source}" ]]; then
            printf 'SOURCE_VIEW_NOT_AVAILABLE=%s\n' "${view_source}" > "${view_root}/availability.log"
            continue
        fi
        cp "${view_source}" "${view_root}/${cell}.mag"
        cp "${tech_root}/tech/.magicrc" "${view_root}/.magicrc"
        (
            cd "${view_root}"
            TARGET_CELL="${cell}" magic -dnull -noconsole \
                < "${campaign_root}/diagnostics/drc_leaf.tcl" \
                > drc.log 2>&1
        )
    done

    lvs_root="${result_root}/${cell}/lvs"
    mkdir -p "${lvs_root}"
    physical_view="${tech_root}/maglef_lib/${cell}.mag"
    schematic_view="${tech_root}/lvs_lib/${cell}.sp"
    if [[ ! -f "${physical_view}" || ! -f "${schematic_view}" ]]; then
        printf 'PHYSICAL_VIEW=%s\nSCHEMATIC_VIEW=%s\n' \
            "$(test -f "${physical_view}" && echo AVAILABLE || echo NOT_AVAILABLE)" \
            "$(test -f "${schematic_view}" && echo AVAILABLE || echo NOT_AVAILABLE)" \
            > "${lvs_root}/availability.log"
        continue
    fi
    cp "${physical_view}" "${lvs_root}/${cell}.mag"
    cp "${schematic_view}" "${lvs_root}/${cell}.schematic.spice"
    cp "${tech_root}/tech/.magicrc" "${lvs_root}/.magicrc"
    cp "${attempt_root}/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl" "${lvs_root}/setup.tcl"
    (
        cd "${lvs_root}"
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

printf 'Attempt05 leaf prequalification complete: %s cells\n' "${#cells[@]}"
