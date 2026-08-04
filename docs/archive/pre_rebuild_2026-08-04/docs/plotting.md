# Strict Plotting Pipeline

The plotting pipeline is strict and factual:

1. Scenario input
2. Scenario resolution
3. Full matching dataset retrieval
4. Validation
5. Pareto/frontier computation
6. Plot generation
7. Plot + metadata artifacts

## Command

```bash
python3 eccsim.py plot pareto \
  --from reports/ \
  --node 7 --vdd 0.8 --temp 25 \
  --scrub-interval-s 5 --capacity-gib 1 \
  --codes sec-ded-64,sec-daec-64,taec-64 \
  --x carbon_kg --y FIT \
  --x-objective min --y-objective min \
  --show-dominated \
  --save-metadata \
  --strict-scenario \
  --error-on-empty \
  --log-x \
  --out reports/plots/pareto_node7_vdd0p8.png
```

## Scenario Filtering

- Categorical fields are matched exactly.
- Float fields use fixed documented tolerances (for example `vdd`, `temp`, `scrub_s`).
- Omitted fields expand the selection scope and are listed in metadata.
- In strict mode, requesting a field absent from data raises an explicit error.

## Data Completeness Rules

- Plotting uses all matching rows; no subsampling is applied unless requested by future explicit options.
- The Pareto frontier is always computed from the full filtered dataset.
- If only reduced artifacts are found, the pipeline attempts recomputation from `scenario.json`.
- If recomputation is not possible, plotting fails with an explanatory error.

## Metadata Sidecar

Each plot writes a JSON sidecar (`.json`) with:

- Scenario requested/applied
- Source files and source-kind counts
- Row counts before dedup, loaded, filtered, plotted, frontier
- Axis columns, objective directions, log transforms
- Timestamp and git hash
- Row-level provenance for plotted points

## Provenance Verification

- Check `source_files` in metadata.
- Check `rows_after_filter` equals the expected scenario row count.
- Verify each `plotted_rows[*]` entry maps back to a source file + row index.
