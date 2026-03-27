# Error-Code-Correction (ECC) Design & Analysis Framework

A research-oriented toolkit for evaluating SRAM ECC choices across **reliability**, **energy**, and **carbon** metrics, then making deterministic multi-objective selections.

The repository combines:
- C++ simulation binaries for ECC/fault workflows,
- Python CLIs for analysis and reporting,
- calibration/config datasets,
- optional ML advisory tooling (fallback-safe; deterministic selector remains the baseline).

---

## Quick Start

```bash
git clone <repo-url>
cd Error-Code-Correction
python3 -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python3 -m pip install -U pip
python3 -m pip install -r requirements.txt

make
make test
python3 -m pytest -q
```

Run a first end-to-end selector example:

```bash
python3 eccsim.py select \
  --codes sec-ded-64,sec-daec-64,taec-64,bch-63 \
  --node 7 --vdd 0.8 --temp 45 \
  --mbu moderate --capacity-gib 16 \
  --ci 0.55 --bitcell-um2 0.08
```

---

## What this project does

This project evaluates ECC options under realistic trade-offs instead of looking at correction strength alone. It helps answer:

- How reliability changes under different fault/severity assumptions.
- What ECC energy overhead looks like at different node/VDD points.
- How embodied + operational carbon combine for a candidate design.
- Which candidates are Pareto-efficient under fit/carbon/latency objectives.

---

## Why it exists

ECC design selection is usually fragmented across separate reliability, power, and sustainability spreadsheets or scripts. This repository provides a reproducible, test-guarded workflow and stable output formats so that comparisons can be rerun and audited.

---

## Who it is for

- **First-time readers**: understand how ECC options are compared in a structured way.
- **Contributors**: extend models, datasets, or CLI paths with regression tests.
- **Researchers/reviewers**: replay results and inspect assumptions and artifacts.
- **Recruiters/hiring teams**: quickly assess technical scope (modeling, tooling, testing, reproducibility).

---

## Main capabilities

- Deterministic ECC selection across reliability/carbon/latency objectives (`eccsim.py select`).
- Reliability calculations and Hazucha-style modeling (`eccsim.py reliability`, `ser_model.py`, `fit.py`).
- Energy estimation with calibration-aware interpolation (`energy_model.py`).
- Carbon estimation in legacy and calibrated modes (`eccsim.py carbon`, `carbon_model.py`, `carbon.py`).
- ESII/NESII-style sustainability scoring (`eccsim.py esii`, `scores.py`, `esii.py`).
- Telemetry ingestion + EPC computation (`parse_telemetry.py`, telemetry schema docs).
- Integrated toolkit workflow producing summary/data/tables/plots outputs (`eccsim.py evaluate|compare|pareto|report`).
- Optional ML advisory path with confidence/OOD gating and deterministic fallback (`eccsim.py ml`, `ml/`, `ecc_selector.py --ml-model`).

---

## Requirements

Inferred from repository configuration:

- **Python**: 3.10+ (recommended by project docs).
- **C++ compiler**: supporting C++17 (`Makefile` uses `-std=c++17`).
- **Build/test tools**: `make`, `pytest`.
- **Python libraries** (`requirements.txt`):
  - `numpy`
  - `pandas`
  - `pytest`
  - `jsonschema`
  - `matplotlib`
  - `pyyaml`
  - `scikit-learn==1.7.2`

---

## Setup and installation

```bash
git clone <repo-url>
cd Error-Code-Correction
python3 -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python3 -m pip install -U pip
python3 -m pip install -r requirements.txt
```

Build C++ binaries:

```bash
make
```

Run project-required validation commands:

```bash
make test
python3 -m pytest -q
```

---

## Usage

Top-level CLI help:

```bash
python3 eccsim.py --help
```

### 1) Energy estimation

```bash
python3 eccsim.py energy \
  --code sec-ded --node 7 --vdd 0.8 --temp 45 \
  --ops 1000000 --lifetime-h 8760
```

### 2) Carbon estimation (legacy + calibrated)

Legacy:

```bash
python3 eccsim.py carbon \
  --areas 0.1,0.2 --alpha 120,140 --ci 0.55 \
  --Edyn 0.01 --Eleak 0.02
```

Calibrated mode:

```bash
python3 eccsim.py carbon \
  --calibrated --node 7 --area-cm2 0.15 --grid-region global_avg \
  --years 5 --accesses-per-day 1000000 \
  --areas 0.1,0.2 --alpha 120,140 --ci 0.55 --Edyn 0.01 --Eleak 0.02
```

### 3) ECC selection

```bash
python3 eccsim.py select \
  --codes sec-ded-64,sec-daec-64,taec-64,bch-63 \
  --node 7 --vdd 0.8 --temp 45 \
  --mbu moderate --capacity-gib 16 \
  --ci 0.55 --bitcell-um2 0.08
```

Optional constraints:

```bash
--constraints fit_max=1e-9,latency_ns_max=10,carbon_kg_max=5
```

### 4) Reliability path

```bash
python3 eccsim.py reliability hazucha --qcrit 0.4 --qs 1.0 --area 1.0
```

### 5) Integrated toolkit workflow

```bash
python3 eccsim.py evaluate \
  --capacity 8 --word-length 64 \
  --node 14 --vdd 0.8 --temp 75 \
  --fault-modes sbu dbu mbu burst \
  --ci 0.55 --grid-score 0.62 --outdir results/run1
```

Config-driven run:

```bash
python3 eccsim.py compare --input-config config.json --outdir results/run2
```

Post-processing:

```bash
python3 eccsim.py pareto --input results/run1/data/all_candidates.csv --outdir results/run1/plots
python3 eccsim.py report --input results/run1/data/all_candidates.csv --outdir results/run1
```

### 6) Optional ML advisory workflow

```bash
python3 eccsim.py ml --help
python3 eccsim.py ml train --help
python3 eccsim.py ml evaluate --help
python3 eccsim.py ml report-card --help
```

---

## Inputs and outputs

### Common inputs

- CLI parameters for node/VDD/temp/workload/fault assumptions.
- Calibration files (`tech_calib.json`, `tech_calib_uncertainty.json`, `carbon_defaults.json`, `config/signoff_thresholds.json`).
- Schema-constrained datasets (`data/`, `schemas/`, `docs/schema/`).
- Optional telemetry CSV for EPC calculation (`parse_telemetry.py`).

### Common outputs

- Terminal summaries for point analyses.
- JSON/CSV artifacts from selection and integrated workflows.
- Plot artifacts from analysis and toolkit plotting paths.
- Example generated artifacts under `reports/examples/`.

Integrated toolkit output layout (`--outdir`):

- `summary/`
- `data/`
- `tables/`
- `plots/`
- `ml/`

---

## Architecture overview

High-level flow:

1. **Reliability backend** computes SER/FIT style metrics (`ser_model.py`, `fit.py`, `mbu.py`, `qcrit_loader.py`).
2. **Energy backend** maps ECC primitive activity to calibrated energy (`energy_model.py`, `gate_energy.hpp`, `src/energy_loader.*`).
3. **Carbon backend** combines embodied + operational terms (`carbon_model.py`, `carbon.py`).
4. **Selector** builds candidate records and applies deterministic multi-objective decision logic (`ecc_selector.py`, `scores.py`).
5. **Orchestration/packaging** handled by CLI entry points (`eccsim.py`, `integrated_toolkit.py`, `analysis/`).
6. **ML advisory** can suggest alternatives but is confidence/OOD-gated and fallback-safe (`ml/`, `ml/sram_advisory.py`).

---

## Project structure

```text
.
├── eccsim.py                  # Main CLI entry point
├── ecc_selector.py            # Deterministic selector + optional ML advisory gate
├── integrated_toolkit.py      # Integrated evaluate/compare/pareto/report workflow
├── energy_model.py            # Energy models + calibration interpolation
├── carbon_model.py            # Calibrated carbon model
├── carbon.py                  # Legacy carbon calculations and helpers
├── ser_model.py / fit.py      # Reliability and FIT modeling utilities
├── parse_telemetry.py         # Telemetry schema validation + EPC computation
├── analysis/                  # Tradeoff, pareto, sensitivity, plotting pipeline
├── ml/                        # Advisory ML lifecycle (dataset/splits/train/evaluate/predict)
├── data/                      # Data assets and lightweight schema artifacts
├── schemas/                   # JSON schema files
├── docs/                      # Design notes, model docs, schema docs, signoff docs
├── tests/                     # Python + C++ tests, smoke tests, golden fixtures
├── reports/                   # Example output artifacts and calibration manifests
├── asic/ / rtl/               # SystemVerilog codecs/wrappers/testbenches and scripts
├── src/                       # Shared C++ sources
├── Makefile                   # Build + test automation
└── requirements.txt           # Python dependencies
```

---

## Important commands

- Build C++ binaries:
  ```bash
  make
  ```
- Run make-based tests:
  ```bash
  make test
  ```
- Run Python test suite:
  ```bash
  python3 -m pytest -q
  ```
- Smoke test script:
  ```bash
  python3 tests/smoke_test.py
  ```
- Print version fingerprint:
  ```bash
  python3 eccsim.py --version
  ```

---

## Example workflow (first-time contributor)

1. Set up a virtual environment and install dependencies.
2. Run `make`, `make test`, and `python3 -m pytest -q` to confirm a healthy baseline.
3. Run one `eccsim.py select` scenario and inspect output.
4. Run `eccsim.py evaluate ... --outdir results/run1` and inspect generated `summary/`, `data/`, and `plots/`.
5. Review related documentation in `docs/` before modifying models.

---

## Limitations and assumptions

- The framework is intended for **comparative design-space exploration**, not transistor-level signoff.
- Models are calibration/data dependent; interpretation should include scenario assumptions.
- Some metrics are proxies designed for ranking consistency across candidates.
- ML outputs are advisory-only; deterministic selection remains the authoritative baseline.

---

## Additional documentation

- `docs/ProjectOverview.md`
- `docs/SimulatorOverview.md`
- `docs/EnergyModel.md`
- `docs/ESII.md`
- `docs/analysis.md`
- `docs/ml_design.md`
- `docs/drift_policy.md`
- `docs/schema/telemetry.md`
- `docs/SIGNOFF_CHECKLIST.md`

---

## Contributing

Please read:
- `CONTRIBUTING.md`
- `SECURITY.md`

When contributing, keep output schema/CLI contracts stable unless introducing explicit new flags and corresponding tests.
