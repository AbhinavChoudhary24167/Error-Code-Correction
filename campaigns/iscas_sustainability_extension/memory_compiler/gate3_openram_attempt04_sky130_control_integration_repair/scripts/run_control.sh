#!/usr/bin/env bash

set -uo pipefail

phase="${1:?usage: run_control.sh PHASE [OPENRAM_SOURCE]}"
openram_source="${2:-/attempt/source/OpenRAM}"
control_config="/attempt/config/control_8x16_config.py"
output_dir="/attempt/output/control_8x16"
work_dir="/attempt/work/control_8x16"
phase_evidence="/attempt/evidence/${phase}"
log_file="/attempt/logs/${phase}_control.log"

if [[ -e "${output_dir}" || -e "${work_dir}" || -e "${phase_evidence}" ]]; then
    echo "refusing non-clean ${phase} run: output, work, or evidence path exists" >&2
    exit 2
fi

source /attempt/venv/bin/activate
export OPENRAM_HOME="${openram_source}/compiler"
export OPENRAM_TECH="${openram_source}/technology"
export PYTHONPATH="${openram_source}/compiler:${openram_source}/technology/sky130:${openram_source}/technology/sky130/custom"
export PDK_ROOT=/attempt/pdk
export VOLARE_HOME=/attempt/pdk/volare
export SPICE_MODEL_DIR=/attempt/pdk/sky130A/libs.tech/ngspice
export OPENRAM_TMP="${work_dir}"

cd "${openram_source}"
python3 sram_compiler.py -v "${control_config}" 2>&1 | tee "${log_file}"
openram_exit=${PIPESTATUS[0]}

mkdir -p "${phase_evidence}"
if [[ -e "${output_dir}" ]]; then
    mv "${output_dir}" "${phase_evidence}/output_control_8x16"
fi
if [[ -e "${work_dir}" ]]; then
    mv "${work_dir}" "${phase_evidence}/work_control_8x16"
fi

printf '%s\n' "${openram_exit}" > "${phase_evidence}/openram_exit_code.txt"
exit "${openram_exit}"
