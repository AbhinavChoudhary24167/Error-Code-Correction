#!/usr/bin/env bash
set -euo pipefail
root_dir=$(dirname "$0")/..
out_dir="$root_dir/reports/examples"

# Parameters for each SKU
# capacity given in GiB (approx)
declare -A sku_capacity
sku_capacity["sku-64b-128Gb"]=16
sku_capacity["sku-32b-1Gb"]=0.125

MBUS=(light moderate heavy)
CIS=(0.30 0.55 0.90)
SCRUBS=(5 10 20 40)

for sku in "${!sku_capacity[@]}"; do
  cap="${sku_capacity[$sku]}"
  base_dir="$out_dir/$sku"
  mkdir -p "$base_dir"
  for mbu in "${MBUS[@]}"; do
    for ci in "${CIS[@]}"; do
      for scrub in "${SCRUBS[@]}"; do
        dir="$base_dir/mbu-${mbu}_ci-${ci}_scrub-${scrub}"
        mkdir -p "$dir"
        python eccsim.py select --codes sec-ded-64,sec-daec-64,taec-64 --node 14 --vdd 0.8 --temp 75 \
          --mbu "$mbu" --scrub-s "$scrub" --capacity-gib "$cap" --ci "$ci" --bitcell-um2 0.040 \
          --report "$dir/pareto.csv" --plot "$dir/pareto.png"
        # Normalise column names for downstream tools
        python - "$dir/pareto.csv" <<'PY'
import pandas as pd, sys
fname=sys.argv[1]
df=pd.read_csv(fname)
df.rename(columns=str.lower, inplace=True)
df.to_csv(fname, index=False)
PY
        python eccsim.py analyze tradeoffs --from "$dir/pareto.csv" --out "$dir/tradeoffs.json" --bootstrap 100 --seed 1 || true
        python eccsim.py analyze archetype --from "$dir/pareto.csv" --out "$dir/archetypes.json" || true
        cat <<SCEN > "$dir/scenario.json"
{
  "codes": ["sec-ded-64", "sec-daec-64", "taec-64"],
  "node": 14,
  "vdd": 0.8,
  "temp": 75.0,
  "capacity_gib": $cap,
  "ci": $ci,
  "bitcell_um2": 0.040,
  "mbu": "$mbu",
  "scrub_s": $scrub
}
SCEN
        python eccsim.py analyze sensitivity --from "$dir/scenario.json" --factor vdd --grid 0.7,0.8,0.9 --out "$dir/sensitivity-vdd.json" || true
      done
    done
  done
done

echo "Artifacts written to $out_dir"
