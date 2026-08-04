#!/usr/bin/env bash
set -euo pipefail
for tb in tb_secded tb_secdaec tb_taec tb_bch tb_polar tb_sram_wrappers tb_green_ecc_selection tb_green_ecc_transition_controller; do
  echo "[RUN] $tb"
  asic/scripts/run.sh "$tb"
done
