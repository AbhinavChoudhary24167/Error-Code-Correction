# Error-Code-Correction Framework Guide

A comprehensive toolkit for exploring error-correcting-code (ECC) schemes in SRAM.
It combines C++ simulators, Python analysis utilities and calibration data to
study reliability, energy cost and environmental footprint.  The project was
originally written for academic research but is packaged so that new users can
reproduce the experiments or extend the framework for their own designs.

This guide overviews the available components, how to build and run them and
where to find deeper documentation.

## Table of Contents
- [Repository Layout](#repository-layout)
- [Quick Start](#quick-start)
- [Dependencies](#dependencies)
- [Building the Simulators](#building-the-simulators)
- [Running the Tools](#running-the-tools)
  - [C++ Memory Simulators](#c-memory-simulators)
  - [Python Utilities](#python-utilities)
- [Interpreting Structured Results](#interpreting-structured-results)
- [Advanced Analysis](#advanced-analysis)
- [Example Workflows](#example-workflows)
- [Testing](#testing)
- [Contributing](#contributing)
- [Additional Documentation](#additional-documentation)
- [License](#license)

## Repository Layout

```
.
├── analysis/             # Reliability and trade‑off analysis helpers
├── data/                 # Sample data files used in tests and examples
├── docs/                 # Additional design notes and background research
├── reports/              # Example outputs produced by helper scripts
├── scripts/              # Helper shell scripts for batch studies
├── src/                  # Shared C++ sources (energy model loader)
├── tests/                # GoogleTest and pytest suites
├── Hamming32bit1Gb.cpp   # SEC‑DED simulator for 32‑bit words
├── Hamming64bit128Gb.cpp # SEC‑DED simulator for 64‑bit words
├── BCHvsHamming.cpp      # BCH(63,51,2) vs. Hamming comparison tool
├── SAT.cpp               # Small DPLL SAT solver demo
├── eccsim.py             # Reliability, energy and carbon modelling CLI
├── ecc_selector.py       # Recommend ECC given BER, burst length and energy
├── energy_model.py       # Gate‑level energy estimator
├── parse_telemetry.py    # Process decoder telemetry CSV logs
├── taec_hamming_sim.py   # Monte‑Carlo TAEC vs. Hamming comparison
└── ...
```

## Quick Start

Clone the repository, install Python dependencies and build the C++ simulators:

```bash
pip install -r requirements.txt
make
./Hamming32bit1Gb              # run a minimal example
```

The sample run prints correction statistics and creates `ecc_stats` and
`decoding_results` logs in the project root.

## Dependencies

### System tools
- **C++17 compiler** (`g++` by default)
- **Make** for convenient builds and test orchestration
- **CMake 3.x** (only required for the optional GoogleTest target)

### Python stack
Install the required packages with:

```bash
pip install -r requirements.txt
```

Dependencies include NumPy, pandas, pytest and jsonschema.  Python 3.8+ is
recommended for full compatibility.

## Building the Simulators

Run `make` to compile all binaries (`BCHvsHamming`, `Hamming32bit1Gb`,
`Hamming64bit128Gb`, `SATDemo`) using the provided `g++` flags (`-std=c++17 -O2`).

For individual builds:

```bash
g++ -std=c++17 Hamming64bit128Gb.cpp -o Hamming64bit128Gb
g++ -std=c++17 Hamming32bit1Gb.cpp -o Hamming32bit1Gb
g++ -std=c++17 BCHvsHamming.cpp -o BCHvsHamming
g++ -std=c++17 SAT.cpp -o SATDemo
```

Cleaning artifacts:

```bash
make clean
```

## Running the Tools

### C++ Memory Simulators

All simulators emit human-readable statistics and structured logs:

- `comparison_results.json` – BCH vs. Hamming outcome table
- `decoding_results.{csv,json}` – per-read traces
- `ecc_stats.{csv,json}` – aggregated ECC metrics

These files live in the repository root and are git-ignored to keep history
clean.  Inspect with spreadsheet tools or `jq`:

```bash
jq '.ber' ecc_stats.json
```

#### Hamming32bit1Gb
Simulates a sparse 1 GB memory using SEC‑DED Hamming codes and a lightweight
Monte‑Carlo comparison against a TAEC scheme.

```
./Hamming32bit1Gb
```

Runs a seven-scenario test suite (no errors, single‑bit, double‑bit, parity‑bit,
burst, random multi‑error, mixed workload) and prints correction/detection
statistics plus energy estimates.  A Monte‑Carlo routine samples common error
patterns to show how SEC‑DED and TAEC differ in coverage.

#### Hamming64bit128Gb
Extends the model to 64‑bit words and a theoretical 128 GB address space.  It
includes a “Million Word Dataset” stress test and optional
`RUN_STRESS_TEST=1` read/write burn‑in.  Like the 32‑bit version it concludes
with a Monte‑Carlo comparison of SEC‑DED and TAEC coverage.

```
./Hamming64bit128Gb
```

Outputs the same `ecc_stats` and `decoding_results` logs as the 32‑bit version.

#### BCH vs Hamming Comparison

```
./BCHvsHamming
```

Runs a side‑by‑side BCH(63,51,2) vs. SEC‑DED Hamming evaluation over multiple
error patterns and saves the summary in `comparison_results.*`.

#### SAT Solver Demo

```
./SATDemo
```

Demonstrates a small DPLL SAT solver used for Hamming‑code conjectures, printing
solver statistics and example proofs.

### Python Utilities

The repository ships several standalone Python modules in addition to the
`eccsim` CLI.  Each tool prints a short help message when invoked with `-h`.

#### `eccsim.py`
Multi‑purpose command line interface for reliability, energy and carbon
modelling.  Key subcommands:

- `eccsim reliability-report` – compute FIT/MTTF numbers for a given ECC.
- `eccsim select` – generate a Pareto frontier of candidate codes.
- `eccsim analyze tradeoffs` – quantify exchange rates on a frontier.
- `eccsim analyze archetype` – attach high‑level archetype labels to designs.

All subcommands share a technology calibration file (`tech_calib.json`) so that
C++ and Python components use consistent energy numbers.

#### `ecc_selector.py`
Recommend an ECC scheme given runtime conditions:

```bash
python3 ecc_selector.py <ber> <burst_length> <vdd> <energy_budget> <required_bits> [--sustainability]
```

Prints the chosen code, correctable bits, burst tolerance, energy estimate and
supported VDD range.

#### `energy_model.py`
Tiny gate‑level energy estimator.  Multiply the number of primitive gate
evaluations by technology-aware energy costs loaded from `tech_calib.json`.

```bash
python3 energy_model.py <parity_bits> [detected_errors]
```

#### `parse_telemetry.py`
Parse decoder telemetry logs and report total energy and per‑correction energy.
Also accessible via `make epc-report` with parameters `CSV`, `NODE` and `VDD`.

```bash
python3 parse_telemetry.py --csv tests/data/sample_secdaec.csv --node 16 --vdd 0.7
```

#### `taec_hamming_sim.py`
Monte‑Carlo comparison of traditional Hamming SEC‑DED and Triple Adjacent Error
Correction (TAEC) codes.  Generates random error patterns and reports how many
are corrected, detected-only or missed by each code.

```bash
python3 taec_hamming_sim.py --trials 10000 --seed 1
```

The script prints the distribution of sampled patterns along with per-code
correction, detection-only and miss rates.

## Interpreting Structured Results

- **`ecc_stats.*`** – aggregate statistics; field `ber` (bit error rate)
  illustrates overall reliability and can be queried with `jq` or loaded into
  pandas.
- **`decoding_results.*`** – per-read logs including addresses, injected errors
  and correction outcomes; useful for deeper debugging.
- **`comparison_results.*`** – summarises BCH vs. Hamming performance across
  test cases.
- **`pareto.csv`** – produced by `eccsim select`; design points forming a Pareto
  frontier.
- **`tradeoffs.json`** / **`archetypes.json`** – outputs from `eccsim analyze`
  providing exchange rates and high-level labels for each point.
- **`sensitivity-vdd.json`** – sensitivity of reliability to supply voltage.

All logs are CSV and JSON so they can be imported into notebooks or spreadsheets
for plotting or further analysis.

## Advanced Analysis

After generating a Pareto frontier with `eccsim select`, additional analysis
commands quantify exchange rates and attach archetype labels to design points:

```bash
eccsim select --codes sec-ded,sec-daec --node 7 --vdd 0.8 --temp 25 --capacity-gib 1 --ci 400 --bitcell-um2 0.1 --report pareto.csv

eccsim analyze tradeoffs --from pareto.csv --out reports/tradeoffs.json \
    --bootstrap 20000 --seed 1 --filter "carbon_kg < 2"

eccsim analyze archetype --from pareto.csv --out reports/archetype.json
```

Energy reports include an explicit `E_scrub_kWh` column capturing background
scrub energy.  JSON summaries set `"includes_scrub_energy": true` to signal that
operational carbon accounts for these reads.

## Example Workflows

Run the helper script to explore multiple reliability scenarios and emit example
artifacts:

```bash
bash scripts/run_sku_studies.sh
```

Versioned results for a light MBU rate, CI=0.55 and 5 s scrub interval are
provided for reference:

- `reports/examples/sku-64b-128Gb/mbu-light_ci-0.55_scrub-5/`
- `reports/examples/sku-32b-1Gb/mbu-light_ci-0.55_scrub-5/`

Each directory includes `pareto.csv`, `tradeoffs.json`, `sensitivity-vdd.json`
and `archetypes.json`.

## Testing

1. Install Python dependencies (see [Dependencies](#dependencies)).
2. Build C++ binaries (`make`).
3. Run the full test suite:

```bash
make test
```

`make test` compiles all simulators, executes a CTest/GoogleTest run and then
invokes both shell and Python tests via pytest.

## Contributing

Contributions are welcome!  Please read [CONTRIBUTING.md](CONTRIBUTING.md) for
the preferred workflow and coding guidelines.

## Additional Documentation

The `docs/` directory contains more background material including implementation
logs, energy model derivations and literature surveys.  Start with
[`docs/SimulatorOverview.md`](docs/SimulatorOverview.md) for a tour of each
simulator.

## License

This project is licensed under the [MIT License](LICENSE).

