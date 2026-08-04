# Reproducibility

The documentation build is executable: it regenerates the scientific inputs before updating prose tables and figures.

## One-command reproduction

From the repository root:

```text
python scripts/build_documentation.py
```

The command performs, in order:

1. `python scripts/build_multi_ecc_catalogue.py`;
2. `python scripts/run_multi_ecc_framework_evaluation.py`;
3. `python scripts/generate_documentation_figures.py`;
4. generated catalogue/result/claim/figure table updates;
5. Markdown link and image validation;
6. JSON example and all documentation/evaluation JSON validation;
7. documentation CSV parsing;
8. figure source/data/output SHA-256 validation;
9. representative CLI `--help` smoke tests;
10. `docs/figure_data/documentation_build_summary.json` emission.

Then verify without modifying files:

```text
python scripts/build_documentation.py --check
```

The check regenerates figures in a temporary directory, compares content hashes, recomputes every marked documentation section, validates links/data/CLI help, and compares the build summary.

## Full project validation

```text
make
make test
python -m pytest -q
```

The repository also supports `python3 -m pytest -q`; activate one environment so `python` and `python3` do not resolve to different installations.

Targeted documentation/Pareto validation is:

```text
python -m pytest -q tests/python/test_documentation_pareto.py
python scripts/generate_documentation_figures.py --check
```

## Deterministic artifacts

The study and documentation pipeline uses:

- canonical sorted JSON and stable ID ordering;
- deterministic matrix generation and exhaustive mask enumeration;
- stable scenario IDs and candidate hashes;
- fixed Matplotlib style and SVG hash salt;
- removed/constant image creation metadata;
- 320-DPI PNG plus vector SVG/PDF from the same in-memory figure;
- one plot-data JSON (and flat CSV where applicable) per scientific figure;
- a figure manifest containing source, data and output SHA-256 hashes;
- an independent Pareto implementation checked against all scenario records.

Run the documentation build twice and compare `git diff` or use `--check`. Substantive generated content must be identical. PDF/PNG/SVG byte hashes are checked, not only their filenames.

## Source-of-truth order

When facts disagree, use:

1. executable source;
2. schemas and registry manifests;
3. tests and verification evidence;
4. freshly regenerated machine-readable evaluation artifacts;
5. provenance- and hash-valid archived logs;
6. documentation.

The historical archive under `docs/archive/pre_rebuild_2026-08-04/` is never consumed by the build.

## Artifact map

| Path | Role |
|---|---|
| `green_ecc_physical_simulation/registry/` | Versioned code/implementation/architecture/backend/scenario/workload manifests |
| `green_ecc_physical_simulation/multi_ecc_evaluation/verification/` | Exact implementation reports and counterexamples |
| `.../characterization/` | Structural/unavailable result records with physical nulls |
| `.../scenario_selection_results.json` | Full candidate/scenario decisions and Pareto sets |
| `.../software_study_summary.json` | Counts, winners, regret, stability and threshold summary |
| `docs/figure_data/` | Plot-ready data, figure manifest and build summary |
| `docs/figures/` | SVG, PNG and PDF outputs |
| `docs/FIGURE_INDEX.md` | Human-readable figure provenance and inclusion map |

## Figure reproduction and inspection

```text
python scripts/generate_documentation_figures.py
python scripts/generate_documentation_figures.py --check
```

Every PNG must be visually inspected for clipping, overlap, contrast, units, legends, null display and evidence overstatement. The PDF/SVG variants are generated from the same Matplotlib figure before it is closed; the manifest binds every format.

## Optional-tool limitations

Icarus Verilog and Yosys can add RTL/structural evidence when present. A commercial or open-source physical flow also requires its exact PDK, libraries, memory collateral, constraints and workload. Reproducibility does not authorize installing or substituting those inputs. If they are absent, the reproducible result is the recorded failed physical gate.
