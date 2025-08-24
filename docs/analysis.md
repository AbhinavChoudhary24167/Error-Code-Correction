# Comprehensive Analysis

This walkthrough demonstrates how to move from raw selection results to a fully
characterized design. The analysis pipeline begins with generating a candidate
set and Pareto frontier, then explores surfaces, trade-offs, sensitivity,
targeted reliability and archetype classification.

## Generate a Frontier
Run `eccsim select` to explore candidate ECC schemes. Emit the full feasible
set and an initial Pareto snapshot:

```bash
eccsim select \
  --codes sec-ded,sec-daec \
  --node 7 --vdd 0.8 --temp 25 \
  --mbu light --scrub-s 5 \
  --capacity-gib 1 --ci 0.55 --bitcell-um2 0.1 \
  --emit-candidates candidates.csv \
  --report pareto.csv
```

The repository ships sample outputs in
`reports/examples/sku-64b-128Gb/mbu-light_ci-0.55_scrub-5/` and
`reports/examples/sku-32b-1Gb/mbu-light_ci-0.55_scrub-5/`.

## Surfaces
Classify the feasible surface and plot it:

```bash
eccsim analyze surface \
  --from-candidates candidates.csv \
  --out-csv pareto.csv \
  --plot surface.png
```

The resulting `pareto.csv` carries a `frontier` column and provenance tags.

## Trade-offs
Quantify exchange rates along the frontier:

```bash
eccsim analyze tradeoffs \
  --from pareto.csv \
  --out tradeoffs.json \
  --bootstrap 20000 --seed 1 \
  --filter "carbon_kg < 2"
```

See `reports/examples/.../tradeoffs.json` for reference.

## Sensitivity
Probe how the recommendation responds to parameter variation. Example:

```bash
eccsim analyze sensitivity \
  --from scenario.json \
  --factor vdd --grid 0.7,0.8,0.9 \
  --out sensitivity-vdd.json
```

The example artifact `sensitivity-vdd.json` under `reports/examples/...` shows a
voltage sweep.

Two-factor runs accept `--factor2`/`--grid2` and optionally `--csv` to emit a matrix.

## Target BER
When a reliability target is known, select the lowest-carbon design that meets
it:

```bash
eccsim target \
  --codes sec-ded,sec-daec \
  --target-type bit --target 1e-8 \
  --node 7 --vdd 0.8 --temp 25 --mbu light --scrub-s 5 \
  --capacity-gib 1 --ci 0.55 --bitcell-um2 0.1 \
  --feasible feasible.csv \
  --choice choice.json
```

`feasible.csv` contains all codes satisfying the BER constraint and `choice.json`
records the minimum-carbon pick.

## Archetypes
Finally, assign qualitative archetype labels:

```bash
eccsim analyze archetype \
  --from pareto.csv \
  --out archetypes.json
```

`reports/examples/.../archetypes.json` illustrates the output format.

This sequence provides a complete user-level path from raw simulation outputs to
high-level design guidance.
