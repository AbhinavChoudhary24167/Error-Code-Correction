#!/usr/bin/env bash
set -euo pipefail
TB=${1:-tb_secded}
mkdir -p asic/out
iverilog -g2012 -f asic/scripts/filelist.f asic/tb/${TB}.sv -o asic/out/${TB}.out
