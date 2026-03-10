#!/usr/bin/env bash
set -euo pipefail
TB=${1:-tb_secded}
asic/scripts/compile.sh "$TB"
vvp asic/out/${TB}.out
