# Developer guide

## Invariants

- Preserve CLI behavior, JSON/CSV field names, and default output formatting.
- Make schema or behavior changes only behind explicit new flags.
- Add rather than refactor frozen research artifacts.
- Put ML code under `ml/`; ML remains advisory and must fall back deterministically.
- Never edit a historical failure into a pass or reseal provenance without a documented migration.

## Local workflow

```bash
python -m pip install -r requirements.txt
make artifact-check
make
make test
python -m pytest -q
git diff --check
```

Run `make help` for maintained entry points. Use `TemporaryDirectory`/pytest temporary paths for generated test data. Do not write UUID fixtures, binaries, compiler products, render pages, or ad hoc logs into tracked paths.

## Change boundaries

Reusable code belongs in `green_ecc_phy/`, `architecture/`, `analysis/`, or `ml/`. Schemas belong in `schemas/`. A self-contained evidence population belongs in a new `campaigns/` subdirectory with its own contract and validation. Keep publication manuscripts and submission PDFs outside this repository; commit only reusable data, figures, reports, and traceability records that support the software or its evidence.

## Tests and review

Add focused unit tests and a regression test for each fixed failure. Preserve golden CLI output for existing interfaces. ML additions require deterministic training, out-of-distribution fallback, and train-to-predict smoke coverage. Reviewers should be able to trace every changed claim to a changed evidence record or explain that it is documentation-only.

## Provenance rules

Record the starting commit, dirty state, command, tool versions, seed, configuration hash, output hashes, timestamps, and resource budget. Use stable identifiers and sorted serialization. Paths in new public automation must be relative or configured; absolute paths are acceptable only inside immutable executed provenance.

See [CONTRIBUTING.md](../CONTRIBUTING.md), [Results schema](results-schema.md), and [Adding an experiment](adding-an-experiment.md).
