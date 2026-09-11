#!/usr/bin/env bash

set -euo pipefail

phase="${1:?usage: primitive_drc_matrix.sh PHASE WORK_DIRECTORY}"
work_directory="${2:?usage: primitive_drc_matrix.sh PHASE WORK_DIRECTORY}"
result_root="/attempt/primitive/${phase}_drc"

source_cells=(
    sky130_fd_bd_sram__openram_dff
    sky130_fd_bd_sram__openram_dp_cell
    sky130_fd_bd_sram__openram_dp_cell_dummy
    sky130_fd_bd_sram__openram_dp_cell_replica
    sky130_fd_bd_sram__openram_sense_amp
    sky130_fd_bd_sram__openram_sp_cell_opt1a_dummy
    sky130_fd_bd_sram__openram_sp_cell_opt1_replica
    sky130_fd_bd_sram__openram_sp_cell_opt1a_replica
    sky130_fd_bd_sram__openram_sp_nand2_dec
    sky130_fd_bd_sram__openram_sp_nand3_dec
    sky130_fd_bd_sram__openram_sp_rowend_replica
    sky130_fd_bd_sram__openram_sp_rowenda_replica
    sky130_fd_bd_sram__openram_write_driver
    sky130_fd_bd_sram__sram_sp_cell_opt1
    sky130_fd_bd_sram__sram_sp_cell_opt1_ce
    sky130_fd_bd_sram__sram_sp_cell_opt1a
    sky130_fd_bd_sram__sram_sp_colend
    sky130_fd_bd_sram__sram_sp_colend_cent
    sky130_fd_bd_sram__sram_sp_colend_p_cent
    sky130_fd_bd_sram__sram_sp_colenda
    sky130_fd_bd_sram__sram_sp_colenda_cent
    sky130_fd_bd_sram__sram_sp_colenda_p_cent
    sky130_fd_bd_sram__sram_sp_corner
    sky130_fd_bd_sram__sram_sp_cornera
    sky130_fd_bd_sram__sram_sp_cornerb
    sky130_fd_bd_sram__sram_sp_rowend
    sky130_fd_bd_sram__sram_sp_rowenda
    sky130_fd_bd_sram__sram_sp_wlstrap
    sky130_fd_bd_sram__sram_sp_wlstrap_ce
    sky130_fd_bd_sram__sram_sp_wlstrap_p
    sky130_fd_bd_sram__sram_sp_wlstrap_p_ce
    sky130_fd_bd_sram__sram_sp_wlstrapa
    sky130_fd_bd_sram__sram_sp_wlstrapa_p
)

generated_cells=(
    sky130_sram_1rw_8x16_gate3a03_control_precharge_0
    sky130_sram_1rw_8x16_gate3a03_control_port_data
    sky130_sram_1rw_8x16_gate3a03_control_write_mask_and_array
    sky130_sram_1rw_8x16_gate3a03_control_sky130_bitcell_array
    sky130_sram_1rw_8x16_gate3a03_control_sky130_dummy_array
    sky130_sram_1rw_8x16_gate3a03_control_sky130_replica_column
    sky130_sram_1rw_8x16_gate3a03_control_sky130_replica_bitcell_array
    sky130_sram_1rw_8x16_gate3a03_control_sky130_capped_replica_bitcell_array
)

mkdir -p "${result_root}"

for view in maglef mag; do
    for cell in "${source_cells[@]}"; do
        source_view="/attempt/source/OpenRAM/technology/sky130/${view}_lib/${cell}.mag"
        if [[ ! -f "${source_view}" ]]; then
            continue
        fi
        cell_root="${result_root}/source_${view}/${cell}"
        mkdir -p "${cell_root}"
        cp /attempt/source/OpenRAM/technology/sky130/tech/.magicrc "${cell_root}/.magicrc"
        cp "${source_view}" "${cell_root}/${cell}.mag"
        (
            cd "${cell_root}"
            PDK_ROOT=/attempt/pdk DRC_CELL="${cell}" \
                magic -dnull -noconsole < /attempt/diagnostics_drc.tcl \
                > "${cell_root}/drc.log" 2>&1
        )
    done
done

for cell in "${generated_cells[@]}"; do
    if [[ ! -f "${work_directory}/${cell}.mag" ]]; then
        continue
    fi
    (
        cd "${work_directory}"
        PDK_ROOT=/attempt/pdk DRC_CELL="${cell}" \
            magic -dnull -noconsole < /attempt/diagnostics_drc.tcl \
            > "${result_root}/generated_${cell}.log" 2>&1
    )
done
