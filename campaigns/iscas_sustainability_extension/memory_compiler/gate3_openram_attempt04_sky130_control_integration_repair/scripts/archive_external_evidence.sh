#!/usr/bin/env bash

set -euo pipefail

external_root="/var/lib/green-ecc-iscas-sustainability/gate3_openram_attempt04_sky130_control_integration_repair"
repository_campaign="/mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction/campaigns/iscas_sustainability_extension/memory_compiler/gate3_openram_attempt04_sky130_control_integration_repair"
raw_root="${repository_campaign}/raw"

mkdir -p "${raw_root}/logs" "${raw_root}/environment" "${raw_root}/diagnostics" \
    "${raw_root}/patches" "${raw_root}/runs"

cp -a "${external_root}/logs/." "${raw_root}/logs/"
cp -a "${external_root}/environment/." "${raw_root}/environment/"
cp -a "${external_root}/primitive/." "${raw_root}/diagnostics/"
cp -a "${external_root}/patches/p1_selected" "${raw_root}/patches/"
cp -a "${external_root}/patches/p2_complete_upstream" "${raw_root}/patches/"

for phase in prepatch p1_lvs_views p2_complete_upstream_lvs_fix; do
    source_phase="${external_root}/evidence/${phase}"
    target_phase="${raw_root}/runs/${phase}"
    output_source="${source_phase}/output_control_8x16"
    work_source="${source_phase}/work_control_8x16"

    mkdir -p "${target_phase}/output_control_8x16" "${target_phase}/work_control_8x16"
    cp "${source_phase}/openram_exit_code.txt" "${target_phase}/"

    cp "${output_source}/sky130_sram_1rw_8x16_gate3a03_control.gds" \
        "${output_source}/sky130_sram_1rw_8x16_gate3a03_control.lef" \
        "${output_source}/sky130_sram_1rw_8x16_gate3a03_control.log" \
        "${output_source}/sky130_sram_1rw_8x16_gate3a03_control.lvs.sp" \
        "${output_source}/sky130_sram_1rw_8x16_gate3a03_control.sp" \
        "${target_phase}/output_control_8x16/"

    cp "${work_source}/sky130_sram_1rw_8x16_gate3a03_control.drc.err" \
        "${work_source}/sky130_sram_1rw_8x16_gate3a03_control.drc.out" \
        "${work_source}/sky130_sram_1rw_8x16_gate3a03_control.ext" \
        "${work_source}/sky130_sram_1rw_8x16_gate3a03_control.ext.err" \
        "${work_source}/sky130_sram_1rw_8x16_gate3a03_control.ext.out" \
        "${work_source}/sky130_sram_1rw_8x16_gate3a03_control.gds" \
        "${work_source}/sky130_sram_1rw_8x16_gate3a03_control.lvs.err" \
        "${work_source}/sky130_sram_1rw_8x16_gate3a03_control.lvs.json" \
        "${work_source}/sky130_sram_1rw_8x16_gate3a03_control.lvs.out" \
        "${work_source}/sky130_sram_1rw_8x16_gate3a03_control.lvs.report" \
        "${work_source}/sky130_sram_1rw_8x16_gate3a03_control.mag" \
        "${work_source}/sky130_sram_1rw_8x16_gate3a03_control.sp" \
        "${work_source}/sky130_sram_1rw_8x16_gate3a03_control.spice" \
        "${work_source}/sky130_fd_bd_sram__sram_sp_cell_opt1.ext" \
        "${work_source}/sky130_fd_bd_sram__sram_sp_cell_opt1.mag" \
        "${work_source}/sky130_fd_bd_sram__sram_sp_cell_opt1a.ext" \
        "${work_source}/sky130_fd_bd_sram__sram_sp_cell_opt1a.mag" \
        "${work_source}/sky130_fd_bd_sram__sram_sp_colend.ext" \
        "${work_source}/sky130_fd_bd_sram__sram_sp_colend.mag" \
        "${work_source}/sky130_fd_bd_sram__sram_sp_colenda.ext" \
        "${work_source}/sky130_fd_bd_sram__sram_sp_colenda.mag" \
        "${target_phase}/work_control_8x16/"
done

printf 'Archived selected raw Attempt04 evidence from %s\n' "${external_root}"
