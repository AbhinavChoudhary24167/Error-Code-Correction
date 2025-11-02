# Error-Code-Correction Framework Guide

The Error-Code-Correction (ECC) framework is a comprehensive laboratory for
studying how different redundancy schemes behave inside static random-access
memories (SRAM). It combines:

- **High-performance C++ simulators** that implement concrete Hamming, TAEC and
  BCH codes under realistic soft-error models.
- **Python analysis tooling** that turns simulation traces into reliability,
  energy and sustainability metrics.
- **Calibrated data packs** that describe modern technology nodes, operational
  voltages, scrub intervals and carbon-conversion factors.

The code base started as a research vehicle for a published study, but it is
structured so that newcomers can reproduce the results, design their own
experiments or plug in a custom ECC architecture. This README is intended to be
an end-to-end manual: it tells you why the repository is organised the way it is,
how to install and build the components, how to feed parameters into the
simulators and, crucially, how to interpret the resulting data sets.

## What This Project Does

Error-code correction (ECC) stores extra parity information so that memory reads
can detect and fix bit flips. Modern SRAM designs face increasingly harsh
radiation environments, so engineers must balance ECC strength against energy,
area and sustainability budgets. This repository provides an end-to-end workflow
for answering those questions:

1. **Model the hardware** – Parameterised C++ simulators emulate different memory
   organisations, fault models and ECC schemes (Hamming, TAEC, BCH).
2. **Calibrate technology data** – JSON files in `configs/`, `data/` and
   `tech_calib.json` describe device reliability, scrub intervals and energy
   costs.
3. **Explore the design space** – Python utilities parse simulator logs, generate
   Pareto frontiers and evaluate carbon impact.
4. **Report and compare** – Helper scripts populate `reports/` with CSV/JSON
   artefacts that summarise the trade-offs between alternative codes.

The remainder of this guide overviews the available components, how to build and
run them and where to find deeper documentation.

## Table of Contents
- [What This Project Does](#what-this-project-does)
- [Repository Layout](#repository-layout)
- [Cloning the Repository](#cloning-the-repository)
- [Environment Setup](#environment-setup)
  - [System Dependencies](#system-dependencies)
  - [Python Dependencies](#python-dependencies)
- [Building the Simulators](#building-the-simulators)
- [Running the Tools](#running-the-tools)
  - [C++ Memory Simulators](#c-memory-simulators)
  - [Python Utilities](#python-utilities)
- [Understanding the CLI Outputs](#understanding-the-cli-outputs)
  - [ECC Statistics](#ecc-statistics)
  - [Selector Recommendations](#selector-recommendations)
  - [Energy and Carbon Reports](#energy-and-carbon-reports)
- [End-to-End Example Workflow](#end-to-end-example-workflow)
- [Interpreting Structured Results](#interpreting-structured-results)
- [Advanced Analysis](#advanced-analysis)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Additional Documentation](#additional-documentation)
- [License](#license)

## Repository Layout

```
.
├── analysis/             # Reliability and trade-off analysis helpers
├── data/                 # Sample data files used in tests and examples
├── docs/                 # Additional design notes and background research
├── reports/              # Example outputs produced by helper scripts
├── scripts/              # Helper shell scripts for batch studies
├── src/                  # Shared C++ sources (energy model loader)
├── tests/                # GoogleTest and pytest suites
├── Hamming32bit1Gb.cpp   # SEC-DED simulator for 32-bit words
├── Hamming64bit128Gb.cpp # SEC-DED simulator for 64-bit words
├── BCHvsHamming.cpp      # BCH(63,51,2) vs. Hamming comparison tool
├── SAT.cpp               # Small DPLL SAT solver demo
├── eccsim.py             # Reliability, energy and carbon modelling CLI
├── ecc_selector.py       # Recommend ECC given BER, burst length and energy
├── energy_model.py       # Gate-level energy estimator
├── parse_telemetry.py    # Process decoder telemetry CSV logs
├── taec_hamming_sim.py   # Monte-Carlo TAEC vs. Hamming comparison
└── ...
```

## Cloning the Repository

All instructions assume a POSIX-like shell (Linux or macOS). Clone with git and
change into the project root:

```bash
git clone https://github.com/<your-org-or-user>/Error-Code-Correction.git
cd Error-Code-Correction
```

> **Tip:** The repository contains large generated reports. The default branch
> only tracks small reference data sets, so the clone remains lightweight.

## Environment Setup

The framework mixes compiled simulators with Python tooling. Installing the
dependencies is a two-step process: first install the system toolchain, then the
Python packages.

### System Dependencies

| Requirement | Reason | Verification |
|-------------|--------|--------------|
| GCC or Clang with C++17 support | Build the Monte-Carlo simulators | `g++ --version` |
| GNU Make | Drive the build recipes provided in `Makefile` | `make --version` |
| CMake ≥ 3.15 (optional) | Configure the GoogleTest harness | `cmake --version` |
| Python 3.8+ | Run the analysis and automation scripts | `python3 --version` |

To install on Debian-based systems:

```bash
sudo apt-get update
sudo apt-get install build-essential cmake python3 python3-pip
```

On macOS, install Xcode command-line tools followed by Homebrew packages:

```bash
xcode-select --install
brew install cmake python
```

### Python Dependencies

Create an isolated environment (recommended for reproducibility) and install the
required packages listed in `requirements.txt`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

The requirements file includes numerical (NumPy, pandas), statistical (SciPy),
data-validation (jsonschema) and testing (pytest) libraries. Each script
documents the minimum subset it needs; the superset ensures every entry point
works out of the box.

## Building the Simulators

The top-level `Makefile` wraps all necessary compiler commands. Run

```bash
make
```

to build every simulator (`Hamming32bit1Gb`, `Hamming64bit128Gb`,
`BCHvsHamming`, `SATDemo`). The build defaults to `g++ -std=c++17 -O2`; set
`CXX=<compiler>` to switch to Clang or a cross toolchain.

Build a single binary by invoking the compiler directly, e.g.:

```bash
g++ -std=c++17 Hamming64bit128Gb.cpp -o Hamming64bit128Gb
```

Clean intermediates with `make clean`. When the optional GoogleTest suite is
configured (see [Testing](#testing)), `cmake --build build` performs the same
compilation steps inside the `build/` directory.

## Running the Tools

### C++ Memory Simulators

All C++ binaries write two things: (1) detailed console logs that describe each
scenario and (2) structured artefacts for downstream analysis. The structured
artefacts are stored in the project root and include:

- `decoding_results.{csv,json}` – a per-memory-access transcript containing the
  injected fault pattern, the ECC syndrome and whether the decoder corrected,
  detected-only or missed the corruption.
- `ecc_stats.{csv,json}` – run-wide aggregates such as observed bit error rate
  (`ber`), undetected error probability, energy per correction and scrub energy
  amortisation.
- `comparison_results.{csv,json}` – head-to-head results when more than one codec
  is executed in the same simulator run (e.g. BCH vs. Hamming).

These files are `.gitignore`d so you can run experiments freely without
polluting version control. Inspect JSON blobs with `jq` or load the CSVs into
Python/pandas for custom analytics:

```bash
jq '.ber' ecc_stats.json
python3 -c 'import pandas as pd; print(pd.read_csv("decoding_results.csv").head())'
```

#### Hamming32bit1Gb

This binary models a 1 GiB memory with 32-bit data words protected by classic
single-error-correction/double-error-detection (SEC-DED) Hamming codes. It also
contains a Monte-Carlo harness that compares SEC-DED with Triple Adjacent Error
Correction (TAEC) for representative multi-bit upset (MBU) patterns.

```bash
./Hamming32bit1Gb
```

The executable iterates through seven curated fault injections: clean read,
single-bit, double-bit, parity-bit, word-aligned bursts, random MBU and a mixed
workload. For each scenario the program prints:

1. **Decoder verdict counts** – numbers of corrected, detected-only and
   undetected events.
2. **Syndrome distribution** – which parity bits fired, useful for diagnosing
   coverage blind spots.
3. **Energy ledger** – dynamic energy from corrections, static scrubbing energy
   amortised over the campaign and estimated carbon impact (kg CO₂e).

The trailing Monte-Carlo phase streams ~10⁵ random error patterns and reports
the delta in coverage between SEC-DED and TAEC. The same information is written
into `decoding_results.*` and `ecc_stats.*`.

#### Hamming64bit128Gb

The 64-bit simulator scales everything up: it enumerates a 128 GiB address space
and introduces long-running endurance tests such as the “Million Word Dataset”.
Set `RUN_STRESS_TEST=1` in the environment to trigger a read/write burn-in that
is intentionally heavy-weight:

```bash
RUN_STRESS_TEST=1 ./Hamming64bit128Gb
```

Because the data set is larger, the resulting `decoding_results.csv` can reach
hundreds of thousands of rows. Filter it with pandas or `csvcut` to isolate
regions of interest.

#### BCH vs Hamming Comparison

`BCHvsHamming` benchmarks a shortened BCH(63,51,2) code against the SEC-DED
Hamming baseline. The binary walks through the same curated error suite and
prints side-by-side verdict counts along with energy and area overheads:

```bash
./BCHvsHamming
```

The resulting `comparison_results.json` includes per-scenario winner labels so
you can script down-selection, for example “prefer BCH whenever double-adjacent
MBUs dominate.”

#### SAT Solver Demo

`SATDemo` is a teaching aide showcasing the DPLL SAT solver that was used to
derive some of the parity-check properties. It accepts CNF files on stdin or
defaults to a built-in sample problem:

```bash
./SATDemo < tests/data/sample_cnf.cnf
```

Expect printed solver statistics (decision depth, conflicts, learned clauses)
followed by either a satisfying assignment or a proof of unsatisfiability.

### Python Utilities

Most users interact with the Python layer through the `eccsim` CLI, but several
single-purpose scripts are exposed as well. All commands support `-h`/`--help`
for an exhaustive list of options and defaults.

#### `eccsim.py`

`eccsim` orchestrates full-stack studies by combining technology calibration
data (`tech_calib.json`), ECC capability tables (`configs/`) and measured energy
models (`data/`). It is organised into nested subcommands:

- `eccsim reliability-report` – evaluate a single ECC configuration and emit
  mean time to failure (MTTF), failures-in-time (FIT) and effective yield. Use it
  when you already know the code structure and want detailed behaviour.
- `eccsim select` – sweep a space of candidate codes (e.g. SEC-DED, SEC-DAEC,
  TAEC) under specific environmental and workload assumptions, producing a CSV
  Pareto frontier annotated with energy and carbon metrics.
- `eccsim analyze tradeoffs` – compute marginal tradeoffs (e.g. ΔFIT per µJ) for
  each point on a frontier.
- `eccsim analyze archetype` – label points according to heuristic operating
  modes (“green minimal energy”, “balanced reliability”, etc.).

Example: producing a reliability report for SEC-DED on a 1 GiB array operating
at 0.8 V and 25 °C with a 5 s scrub interval and a 1e-9 BER target.

```bash
python3 eccsim.py reliability-report \
    --code sec-ded \
    --capacity-gib 1 \
    --vdd 0.8 \
    --temp 25 \
    --scrub-interval-s 5 \
    --node 7 \
    --target-ber 1e-9
```

The command prints a human-readable table plus writes `reports/reliability.json`
(overridable via `--out`). Columns include FIT, MTTF hours, detected-only events,
corrected events and uncorrected events. Any warnings (for example insufficient
redundancy) are emitted to stderr.

#### `ecc_selector.py`

This convenience script answers the question “Which ECC should I deploy under my
current error environment?” Invoke it with the observed or expected conditions:

```bash
python3 ecc_selector.py \
    --ber 1e-7 \
    --burst-length 3 \
    --vdd 0.8 \
    --energy-budget-nj 45 \
    --required-bits 64 \
    --sustainability
```

**Input interpretation**

- `--ber` – Raw bit error rate measured before correction.
- `--burst-length` – Maximum consecutive bits affected by a single event (MBU
  length).
- `--vdd` – Supply voltage of the memory macro in volts.
- `--energy-budget-nj` – Decoder energy allowance per access in nanojoules.
- `--required-bits` – Minimum data payload width demanded by the system.
- `--sustainability` (flag) – Include carbon metrics when ranking.

**Output interpretation**

The script prints a textual summary such as:

```
Recommended code : SEC-DAEC-64b
Corrects         : 2 adjacent bit errors
Detects          : up to 3 dispersed errors
Energy           : 38.5 nJ (within budget)
Voltage window   : 0.72 V – 0.90 V
Carbon intensity : 1.7 g CO2e / 10^12 accesses
Reasoning        : Meets burst constraint while minimising carbon impact.
```

It also writes `selector_decision.json` summarising the ranked alternatives with
fields `code`, `score`, `constraints_satisfied`, `energy_nj` and
`carbon_g_per_tb`. This makes it easy to feed the selection into CI pipelines.

#### `energy_model.py`

`energy_model.py` offers a quick analytical estimate of decoder energy when a
full simulation is unnecessary. Supply the number of parity bits and, if known,
the average number of detected-but-uncorrected errors per access as positional
arguments. Optional flags let you override the process node and supply
voltage:

```bash
python3 energy_model.py 8 2 --node 7 --vdd 0.7
```

The script multiplies gate toggles by the calibrated per-gate energies in
`tech_calib.json` and prints a single joule estimate to standard output (for
example `Estimated energy per read: 3.42e-11 J`). Use shell redirection if you
want to persist the value.

#### `parse_telemetry.py`

Use this script to post-process hardware telemetry logs captured from silicon or
RTL emulation. Each row is expected to contain timestamps, correction counts and
energy meter readings. Run:

```bash
python3 parse_telemetry.py tests/data/sample_secdaec.csv \
    --out-csv reports/telemetry_normalized.csv \
    --out-json reports/telemetry_normalized.json
```

The CLI validates the input against `docs/schema/telemetry.schema.json` and
writes normalised CSV/JSON files in canonical column order. Downstream tooling
can ingest those normalised artifacts to compute summaries such as energy per
correction with helper functions like `parse_telemetry.compute_epc`.

#### `taec_hamming_sim.py`

This script mirrors the C++ Monte-Carlo experiment in pure Python for quick
iteration. Provide the number of trials and, optionally, a random seed for
reproducibility:

```bash
python3 taec_hamming_sim.py --trials 10000 --seed 1
```

Standard output contains a three-column table (`pattern`, `sec_ded`, `taec`)
with the proportion of trials falling into each verdict class. Use it to sanity
check analytical approximations before launching long-running C++ campaigns.

## Understanding the CLI Outputs

Each command produces structured data intended for automated pipelines. The
sections below explain how to read the most common outputs and relate them back
to engineering decisions.

### ECC Statistics

Files named `ecc_stats.json` or `reports/reliability.json` share a schema:

| Field | Meaning | Usage suggestion |
|-------|---------|------------------|
| `ber` | Observed bit error rate at the memory interface | Compare against service-level objectives |
| `undetected_rate` | Fraction of accesses where the error escaped detection | Must be ≈0 for safety-critical apps |
| `corrected_rate` | Fraction of accesses successfully repaired | Indicates decoder workload |
| `energy_per_access_nj` | Average decoder energy in nanojoules | Feed into power budgeting |
| `scrub_energy_kwh` | Energy spent on background scrubbing | Accounted for in carbon reporting |
| `carbon_kg` | Life-cycle carbon equivalent | Align with sustainability targets |

When a simulator run finishes you should first check `undetected_rate`; values
above 10⁻¹² typically violate reliability standards. Next review
`energy_per_access_nj` to ensure the decoder fits within thermal envelopes.

### Selector Recommendations

`selector_decision.json` comprises an ordered list of candidate codes, each with
both hard constraint checks and soft scores. A typical entry looks like:

```json
{
  "code": "SEC-DAEC-64b",
  "score": 0.87,
  "constraints_satisfied": ["ber", "burst", "energy", "width"],
  "energy_nj": 38.5,
  "carbon_g_per_tb": 1.7,
  "explanations": [
    "Corrects up to 2 adjacent bit errors.",
    "Fits within 45 nJ energy budget.",
    "Lowest carbon footprint among feasible options."
  ]
}
```

`score` is a weighted composite of energy, carbon and resilience targets. Use
the `explanations` array in design reviews to justify the selection.

### Energy and Carbon Reports

Energy-focused tools (`energy_model.py`, `parse_telemetry.py`, `eccsim analyze
tradeoffs`) emit JSON containing both instantaneous and amortised numbers.
Highlights include:

- `dynamic_j` vs. `static_j`: emphasise how much of the budget is attributable to
  active corrections versus standby scrubbing.
- `carbon_intensity_g_per_tb`: greenhouse-gas emission per terabyte of traffic,
  which is essential when negotiating sustainability budgets with platform
  teams.
- `confidence_interval`: bootstrap range (if requested) for probabilistic
  outputs; the default is 95%.

Always inspect the `assumptions` block embedded in each JSON artefact. It
captures inputs such as ambient temperature, supply voltage and error
distribution – vital for reproducibility.

## End-to-End Example Workflow

The following walk-through mirrors the process used in the accompanying
publication. It takes the reader from cloning through decision-making.

1. **Clone and bootstrap**

   ```bash
   git clone https://github.com/<your-org-or-user>/Error-Code-Correction.git
   cd Error-Code-Correction
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   make
   ```

2. **Generate baseline simulator data**

   ```bash
   ./Hamming32bit1Gb > logs/hamming32.txt
   ./BCHvsHamming > logs/bch_vs_hamming.txt
   ```

   Inspect `logs/*.txt` for human-readable summaries. Structured CSV/JSON files
   appear alongside them in the repository root.

3. **Select candidate ECCs for a 7 nm, 0.8 V, 1 GiB SRAM**

   ```bash
   python3 eccsim.py select \
       --codes sec-ded,sec-daec,taec \
       --node 7 \
       --vdd 0.8 \
       --temp 25 \
       --capacity-gib 1 \
       --ci 400 \
       --bitcell-um2 0.1 \
       --report pareto.csv
   ```

   `pareto.csv` now contains the frontier; the CLI prints a short ranking table
   to stdout.

4. **Quantify energy/reliability tradeoffs**

   ```bash
   python3 eccsim.py analyze tradeoffs \
       --from pareto.csv \
       --out reports/tradeoffs.json \
       --bootstrap 20000 \
       --seed 1
   ```

   Inspect `reports/tradeoffs.json` to understand marginal gains of adding extra
   parity bits.

5. **Summarise for decision-makers**

   ```bash
   python3 eccsim.py analyze archetype --from pareto.csv --out reports/archetypes.json
   python3 ecc_selector.py --ber 1e-7 --burst-length 3 --vdd 0.8 --energy-budget-nj 45 --required-bits 64 --sustainability
   ```

   Use the selector output and archetype labels in review slides. All artefacts
   now live under `reports/` and can be archived with the project documentation.

## Interpreting Structured Results

A quick reference to the on-disk artefacts discussed above:

- **`decoding_results.{csv,json}`** – Access-by-access transcript with columns
  (`address`, `fault_pattern`, `syndrome`, `verdict`, `energy_nj`).
- **`ecc_stats.{csv,json}`** – Aggregated reliability and energy metrics with
  clearly labelled units.
- **`comparison_results.{csv,json}`** – Head-to-head scenario summaries used by
  `BCHvsHamming`.
- **`pareto.csv`** – Output from `eccsim select`; columns include `code`, `fit`,
  `energy_nj`, `carbon_g`, `correctable_bits` and `dominates` flags.
- **`tradeoffs.json`** / **`archetypes.json`** – Derived analyses that quantify
  exchange rates and assign product-readiness labels.
- **`sensitivity-vdd.json`** – Reliability gradients with respect to supply
  voltage, useful when power-management teams propose new operating points.

Every JSON document embeds an `inputs` section. Archive these files together
with your presentation or publication to guarantee reproducibility.

## Advanced Analysis

`eccsim` exposes several knobs to tailor the search space and to constrain
outputs:

- **Filtering** – Pass `--filter "carbon_kg < 2 and fit < 10"` to `eccsim analyze
  tradeoffs` to focus on production-feasible designs.
- **Bootstrap precision** – Increase `--bootstrap` iterations when you need
  tighter confidence intervals; expect runtime to scale linearly.
- **Custom technology files** – Duplicate `tech_calib.json` and edit the supply
  voltage tables or energy-per-gate entries to match your silicon process. Then
  point all commands at it via `--tech-calib <path>`.
- **Sustainability overlays** – Set `--with-carbon-defaults` to merge
  region-specific carbon intensity data from `carbon_defaults.json`.

All reports flag whether scrub energy has been included. Watch for the
`"includes_scrub_energy": true` boolean to make sure sustainability reviews
compare apples to apples.

## Testing

1. Install the Python dependencies (see [Environment Setup](#environment-setup)).
2. Build the C++ simulators (`make`).
3. Execute the full regression suite:

   ```bash
   make test
   ```

`make test` triggers three layers of validation:

- `ctest` runs unit tests in `tests/cpp/` (requires CMake configuration).
- `pytest` executes behavioural tests for the Python modules under `tests/`.
- Shell-based smoke tests ensure scripts such as `scripts/run_sku_studies.sh`
  still produce artefacts.

The command emits consolidated JUnit XML under `build/test-results/`, suitable
for CI ingestion.

## Troubleshooting

- **Compiler errors about missing headers** – Ensure you are compiling with
  C++17 and that your system libraries are up to date. On Debian, install
  `libstdc++-12-dev` or newer.
- **`ModuleNotFoundError` for Python packages** – Activate the virtual
  environment (`source .venv/bin/activate`) before running scripts or add the
  `--user` flag when invoking `pip`.
- **JSON schema validation failures** – Run `python3 scripts/validate_configs.py`
  (provided in `scripts/`) to check edited configuration files against the
  schemas in `schemas/`.
- **Large CSVs slow down analysis** – Use `python3 eccsim.py analyze tradeoffs
  --from pareto.csv --sample 200` to operate on a representative subset.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for the
preferred workflow and coding guidelines.

## Additional Documentation

The `docs/` directory aggregates background material including implementation
logs, energy model derivations and literature surveys. Start with
[`docs/ProjectOverview.md`](docs/ProjectOverview.md) for a description of how the
toolkit pieces fit together, then read
[`docs/SimulatorOverview.md`](docs/SimulatorOverview.md) for a tour of each
simulator. Teams preparing for tape-in can consult
[`docs/AdoptionPlaybook.md`](docs/AdoptionPlaybook.md) for an input/output
checklist and SLA mapping, while
[`docs/Thesis/IEEE_Manuscript.md`](docs/Thesis/IEEE_Manuscript.md) packages the
methodology, quantitative results and references in publication form.

## License

This project is licensed under the [MIT License](LICENSE).
