# Command-line reference

`python eccsim.py --help` is the executable authority. The tables below document every current public command path. Use `python eccsim.py <command> --help` (and the nested command where shown) for the exact current flags.

## Registry, verification, characterization, and physical selection

| Command path | Purpose | Evidence boundary |
|---|---|---|
| `ecc list` | List mathematical codes and implementation counts | Registry exact |
| `ecc inspect --code ID` | Inspect one code, matrix/distance identity and hashes | Registry/exact |
| `ecc implementations --code ID` | List concrete decoder implementations for a code | Registry/exact |
| `ecc verify --implementation ID [--out FILE]` | Run the implementation evidence gate | Exact functional + bound RTL/reference evidence |
| `characterize --implementation ID [--architecture ID] --backend FILE --workload FILE --outdir DIR` | Characterize one passing implementation/architecture | Backend-labelled; null-safe |
| `characterize-all --backend FILE --workload FILE --outdir DIR` | Characterize every passing registered implementation | Backend-labelled; null-safe |
| `select-physical --characterization DIR --scenario FILE --outdir DIR` | Select only fair physical results | Returns no winner when objectives are null/non-physical |
| `doctor [--json] [--strict]` | Diagnose Python, packages, native tools, project files and runtime compatibility | Environment evidence |

## Code synthesis, architecture, and safety workflows

| Command path | Purpose |
|---|---|
| `architecture --config FILE --outdir DIR` | Architecture-aware ECC design-space exploration and deployable configuration |
| `schedule --config FILE --outdir DIR` | Transition-aware scheduling over ordered traces |
| `forge-code --config FILE --outdir DIR` | Synthesize and independently certify a short systematic binary ECC |
| `forge-portfolio --config FILE --outdir DIR` | Joint code-portfolio and shared-XOR-graph search |
| `verify-code --code FILE --fault-model FILE [--out FILE]` | Verify an external/GREEN-ECC linear code against a fault probability mass function |
| `audit-equivalence --code FILE [--reference FILE] [--geometry-rows N] [--geometry-columns N] [--out FILE]` | Classify matrix equivalence without novelty overclaim |
| `compile-safe-decoder --code FILE --fault-model FILE --ambiguity FILE --sdc-limit X [--residual-fit-limit X] --outdir DIR` | Compile an abstaining syndrome policy and exact safety certificate |
| `verify-safety-certificate --certificate FILE [--out FILE]` | Solver-free verification of an external safety certificate |

## Legacy analytical models and selectors

These interfaces predate the normalized multi-ECC identity chain. They remain backward compatible, but legacy family aliases and surrogate constants do not map one-to-one to registered implementation IDs. Do not compare their “winner” directly with the multi-ECC scenario winner without an explicit mapping audit.

| Command path | Purpose |
|---|---|
| `energy ...` | Estimate family-level dynamic/leakage energy; optional uncertainty/sanity flags |
| `carbon ...` | Estimate static/dynamic carbon; calibrated mode is explicit |
| `esii ...` | Compute Energy–Sustainability–Integrity Index inputs/output |
| `select ...` | Legacy weighted multi-objective family selector |
| `target ...` | Minimum-carbon legacy family meeting bit/UWER target |
| `analyze tradeoffs --from FILE --out FILE ...` | Bootstrap trade-off analysis |
| `analyze archetype --from FILE --out FILE` | Classify candidate archetypes |
| `analyze surface --from-candidates FILE --out-csv FILE [--plot FILE]` | Analyze a feasible candidate surface |
| `analyze sensitivity --factor ... --from FILE --out FILE` | One- or two-factor sensitivity analysis |
| `plot pareto --from FILE --out FILE ...` | Strict scenario-filtered two-objective plot with explicit directions |
| `reliability hazucha --qcrit ... --qs ... --area ...` | Hazucha–Svensson-style SER calculation |
| `reliability report ...` | Combined SER, MBU, scrub, ECC and environment report |

## SRAM and optional ML workflows

| Command path | Purpose |
|---|---|
| `sram simulate ...` | Seeded SRAM ECC simulation |
| `sram stress ...` | Larger seeded stress campaign |
| `sram compare ...` | Compare legacy SRAM scheme aliases |
| `sram select ...` | Deterministic SRAM selector with optional advisory ML |
| `ml build-dataset --from DIR --out DIR ...` | Build a deterministic advisory dataset |
| `ml split-dataset --dataset DIR ...` | Create deterministic train/validation/holdout splits |
| `ml train --dataset DIR --model-out DIR ...` | Train the advisory model and OOD/confidence metadata |
| `ml evaluate --dataset DIR --model DIR --out DIR ...` | Evaluate model, fallback and optional sign-off thresholds |
| `ml check-drift --model DIR --new-data DIR ...` | Compute drift and optional policy action report |
| `ml report-card --model DIR [--out FILE]` | Generate a model report card |

ML remains advisory-only; the deterministic selector is the baseline and out-of-distribution (OOD) or low-confidence inputs fall back.

## Integrated toolkit compatibility commands

| Command path | Purpose |
|---|---|
| `evaluate --capacity ... --word-length ... --outdir DIR` | Integrated SRAM ECC evaluation |
| `compare --input-config FILE --outdir DIR` | Integrated evaluation from JSON configuration |
| `pareto --input FILE --outdir DIR` | Generate integrated CSV Pareto plots |
| `report --input FILE --outdir DIR` | Regenerate integrated report from `all_candidates.csv` |
| `ml-infer --input-config FILE --model DIR --outdir DIR` | Integrated evaluation with advisory ML |

## Reproducible multi-ECC and documentation scripts

| Command | Purpose | Local status |
|---|---|---|
| `python scripts/build_multi_ecc_catalogue.py` | Regenerate validated registry catalogue | Verified locally |
| `python scripts/run_multi_ecc_framework_evaluation.py` | Regenerate verification, characterization and analytical study | Verified locally |
| `python scripts/generate_documentation_figures.py` | Generate 17 plots, data and provenance manifest | Verified locally |
| `python scripts/generate_documentation_figures.py --check` | Non-mutating figure staleness check | Verified locally |
| `python scripts/build_documentation.py` | Complete documentation reproduction | Verified locally after suite generation |
| `python scripts/build_documentation.py --check` | Non-mutating documentation validation | Verified locally after suite generation |

## Current verified examples

```text
python eccsim.py ecc list
python eccsim.py ecc inspect --code hsiao-secded-72-64-v1
python eccsim.py ecc implementations --code extended-hamming-secded-72-64-v1
python eccsim.py ecc verify --implementation hsiao-generated-combinational-72-64-v1
python eccsim.py ecc verify --implementation secdaec-rtl-bounded-72-64-v1
```

The rejected verification example intentionally emits a negative scientific result. See [Getting Started](GETTING_STARTED.md) for interpretation and [Troubleshooting](TROUBLESHOOTING.md) for exact error classes.
