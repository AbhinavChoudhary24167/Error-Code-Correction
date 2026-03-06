# Error-Code-Correction (ECC) Design & Analysis Framework

A research-to-engineering toolkit for evaluating memory error-correction codes (ECC) across **reliability**, **energy**, **latency**, and **carbon** constraints.

This repository combines C++ simulators, Python analytics, and calibrated technology data so teams can move from “which code corrects more errors?” to “which code is best for this product target?”.

---

## Who this is for

- **General users / students** who want to run ECC simulations and compare schemes quickly.
- **Firmware/architecture engineers** choosing an ECC strategy under BER/UWER, energy, and scrub constraints.
- **Reliability and sustainability teams** quantifying how ECC decisions impact operational + embodied carbon.
- **Researchers** extending baseline models with additional codes, workloads, or advisory ML.

---

## What problem this framework solves

Modern SRAM deployments (edge devices, accelerators, data centers, radiation-sensitive systems) must tolerate soft errors while staying inside strict power and area budgets. Traditional ECC evaluations often stop at correction capability. This framework explicitly unifies:

1. **Fault behavior** (single-bit, adjacent multi-bit upset, random bursts).
2. **Decoder capability** (SEC-DED, SEC-DAEC, TAEC, BCH, Polar variants).
3. **System-level costs** (latency, scrub overhead, energy).
4. **Sustainability outcomes** (kgCO2e from operation + embodied assumptions).

Result: you get decision-ready outputs, not just syndrome-level correctness.

---

## Why this is novel

Many ECC studies and internal tools rely on one of these narrow workflows:

- **Capability-only comparisons** (e.g., “code A corrects up to t errors”).
- **Single-score decision matrices** with fixed hand-tuned weights and no Pareto visibility.
- **One-off Monte Carlo scripts** disconnected from calibration and reporting.

This project is different in a few important ways:

1. **Multi-objective first, not afterthought**  
   The selector computes Pareto frontiers over FIT, carbon, and latency, then supports knee/hypervolume style trade-off analysis.

2. **Physics + operations + sustainability in one loop**  
   Reliability metrics are connected to scrub policy, node calibration, and carbon factors so recommendations reflect deployment reality.

3. **Baseline + advisory ML architecture**  
   The deterministic selector remains the source of truth; ML support is additive/advisory and does not silently replace the baseline path.

4. **Reproducible artifact contract**  
   CLI and simulators emit structured JSON/CSV outputs used by tests and downstream analysis, enabling automation and regression checks.

---

## How this differs from commonly used “matrices”

When teams say “we use matrices,” they usually mean one of two things:

### A) Static decision matrices (weighted scorecards)
A common approach is a spreadsheet where each ECC gets a score on reliability/power/area and a weighted total.

**Limitations**
- hides non-dominated options,
- sensitive to arbitrary weight tuning,
- weak at handling threshold constraints (e.g., must satisfy UWER target first).

**This framework instead**
- computes objective metrics directly,
- finds Pareto-optimal candidates,
- supports target-constrained selection (e.g., minimum-carbon option that still meets reliability).

### B) Pure parity-check/generator matrix analysis
Code-theory matrix methods are essential, but by themselves they usually answer code-level correctness questions.

**Limitations**
- do not automatically capture system effects like scrub cadence, workload severity, or node-level energy calibration.

**This framework instead**
- preserves code-level simulation detail,
- then elevates results to product decisions (FIT/energy/carbon/latency trade-offs).

In short, parity-check mathematics remains necessary, but not sufficient for architecture decisions. This repository bridges that gap.

---

## Why teams may prefer this framework

- **Decision quality:** exposes Pareto trade-offs instead of forcing premature single-score collapse.
- **Traceability:** recommendation can be traced back to explicit assumptions and artifact files.
- **Reproducibility:** Makefile + pytest coverage + golden outputs guard against silent regressions.
- **Extensibility:** new models can be added under clear module boundaries (`analysis/`, `ml/`, C++ simulators).

---

## Repository map

```text
.
├── Hamming32bit1Gb.cpp        # SEC-DED style simulator + telemetry outputs
├── Hamming64bit128Gb.cpp      # 64-bit scale simulator with stress scenarios
├── BCHvsHamming.cpp           # Head-to-head code comparison workflow
├── SAT.cpp                    # SAT-based educational checks on ECC properties
├── src/                       # Shared C++ code (BCH core, energy loader)
├── eccsim.py                  # Main multi-command CLI
├── ecc_selector.py            # Multi-objective selector and Pareto helpers
├── analysis/                  # Trade-off, knee, HV, sensitivity utilities
├── ml/                        # Advisory ML dataset/train/evaluate/predict flows
├── docs/                      # Design docs, schema, implementation notes
├── reports/                   # Example generated study outputs
├── tests/                     # Python + C++ tests, golden CLI artifacts
└── web/                       # Static dashboard assets
```

---

## Quick start (most users)

### 1) Clone and install

```bash
git clone <your-fork-or-org>/Error-Code-Correction.git
cd Error-Code-Correction
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

### 2) Build simulators

```bash
make
```

### 3) Run the main CLI

```bash
python3 eccsim.py --help
```

### 4) Example analyses

```bash
# Reliability/selection flow
python3 eccsim.py select --codes sec-ded-64,sec-daec-64,taec-64,bch-63 --node 7 --vdd 0.8 --temp 45 --mbu moderate --capacity-gib 16 --ci 400 --bitcell-um2 0.08

# Target-constrained choice (example)
python3 eccsim.py target --codes sec-ded-64,sec-daec-64,taec-64,bch-63 --target-type uwer --target 1e-15 --node 7 --vdd 0.8 --temp 45 --mbu moderate --capacity-gib 16 --ci 400 --bitcell-um2 0.08
```

### 5) Run test suite

```bash
make test
python3 -m pytest -q
```

---

## Technical deep dive (for engineers)

### 1) Simulation layer (C++)

- Sparse memory-backed simulators inject controlled fault patterns.
- Multiple scenario classes are evaluated (single-bit, double-bit, burst/multi-bit upsets).
- Structured outputs are produced for downstream automation (`ecc_stats.*`, `decoding_results.*`, comparison outputs).

### 2) Modeling and selection layer (Python)

- Reliability metrics, SER/FIT transformations, and coverage assumptions are composed into comparative records.
- Multi-objective optimization primitives (Pareto filtering, knee analysis, hypervolume/spacing) quantify design trade-offs.
- Additional sustainability indicators (ESII/GS-style metrics) allow policy-aware ranking.

### 3) Calibration/data layer

- Tech and energy defaults are encoded in JSON artifacts and loaders.
- Telemetry parsing normalizes externally captured logs into schema-compatible data.
- Example report directories demonstrate expected output contract and study structure.

### 4) ML advisory layer

- ML code lives under `ml/` and supports train/evaluate/predict/explain workflows.
- ML is explicitly advisory: baseline deterministic selection remains available and should be treated as primary unless policy says otherwise.

---

## Typical end-to-end workflow

1. Choose technology assumptions and reliability targets.
2. Run one or more simulators to generate correction/error telemetry.
3. Feed data into `eccsim.py` commands for reliability, carbon, and candidate selection.
4. Inspect Pareto outputs and sensitivity analyses.
5. Export/report selected candidate with rationale and assumptions.

---

## Outputs you can expect

Depending on workflow, artifacts may include:

- `ecc_stats.csv/json`
- `decoding_results.csv/json`
- `comparison_results.csv/json`
- Pareto/trade-off/sensitivity outputs under `reports/` and analysis scripts
- Golden-reference-compatible CLI outputs used by tests

These outputs are designed for scripting and reproducible CI checks.

---

## Design principles

- **Backward compatibility first** for interfaces and outputs.
- **Additive evolution** over disruptive refactors.
- **Output schema stability** for JSON/CSV contracts.
- **Deterministic baseline behavior** with optional advisory extensions.

---

## Common use cases

- Selecting ECC for a new SRAM SKU under BER and energy constraints.
- Comparing stronger correction vs. increased decode/scrub overhead.
- Quantifying operational carbon impact of reliability policy changes.
- Generating publication-grade trade-off artifacts from reproducible command lines.

---

## Documentation index

For deeper details, see:

- `docs/ProjectOverview.md` – architecture and workflow context
- `docs/SimulatorOverview.md` – simulator behavior and outputs
- `docs/EnergyModel.md` – energy modeling assumptions
- `docs/ESII.md` – sustainability index details
- `docs/analysis.md` – analysis scripts and parameter sweeps
- `docs/ml_design.md` – ML scope and implementation choices
- `docs/schema/telemetry.md` + schema JSON – telemetry contract

---

## Contributing

Please read:

- `CONTRIBUTING.md`
- `SECURITY.md`

When extending the platform, preserve output contracts and add tests (including golden output coverage where applicable).

---

## License

MIT License (see `LICENSE`).
