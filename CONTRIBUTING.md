# Contributing

Contributions are welcome when they preserve compatibility, scientific provenance, and explicit evidence boundaries. By participating, follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Before opening a change

Discuss broad schema, CLI, evidence-tier, or experiment-design changes before implementation. Existing CLI behavior, default formatting, and JSON/CSV fields are compatibility contracts. Add new flags or versioned fields instead of changing their meaning.

Never rewrite frozen campaign evidence, delete negative results, promote a partial run, or replace null with zero. A new campaign receives a new ID and directory. Machine-specific paths belong only in executed provenance; reusable code uses relative paths or configuration.

## Development setup

```bash
python -m venv .venv
# activate .venv for your shell
python -m pip install -r requirements.txt
make reviewer-smoke
```

For the native build, install GNU Make and a C++17 compiler. Optional RTL/physical tools are documented in [Installation](docs/INSTALLATION.md).

## Required validation

Run from the repository root:

```bash
make
make test
python -m pytest -q
python scripts/check_artifact.py
git diff --check
```

Add focused unit/regression coverage and preserve golden CLI outputs. ML code belongs under `ml/`, remains advisory, and requires deterministic training, OOD fallback, and train-to-predict smoke tests. Generated test data must use temporary directories and must not be committed.

## Evidence and manuscripts

Every experiment must declare identities, useful-payload functional unit, tools/PDK/PVT, workloads/fault populations, seeds, resource budget, expected artifacts, hashes, and failure semantics before execution. Retain raw reports and logs alongside normalized records. Manuscript claims, tables, and figures must trace to the evidence package; presentation does not upgrade evidence.

See the [Developer guide](docs/developer-guide.md), [Adding an ECC](docs/adding-an-ecc.md), [Adding an experiment](docs/adding-an-experiment.md), and [Results schema](docs/results-schema.md).

## Pull requests

Keep changes focused and describe: scientific intent; compatibility impact; commands run; result/claim changes; added evidence and its tier; retained failures; and any unavailable validation. Do not include local binaries, temporary renders, caches, credentials, private datasets, or unlicensed third-party material.
