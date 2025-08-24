# Error-Code-Correction Framework Guide

This repository collects C++ and Python tools for exploring error-correcting-code (ECC) schemes in SRAM and evaluating their reliability, energy cost and environmental footprint. It includes standalone memory simulators, comparison utilities and analytical scripts.

---

## 1. Dependencies

### System tools
- **C++17 compiler** (`g++` by default)
- **Make** for convenient builds and test orchestration
- **CMake 3.x** (only required for the optional GoogleTest target)

### Python stack
Install the required packages with:

```bash
pip install -r requirements.txt
```

Dependencies: NumPy, pandas, pytest and jsonschema. Use Python 3.8+ for best compatibility.

---

## 2. Building the Simulators

Run `make` to compile all binaries (`BCHvsHamming`, `Hamming32bit1Gb`, `Hamming64bit128Gb`, `SATDemo`) using the provided `g++` flags (`-std=c++17 -O2`).

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

---

## 3. Running the Tools & Interpreting Results

### 3.1 Memory Simulators

All simulators emit human-readable statistics and structured logs:

- `comparison_results.json` – BCH vs. Hamming outcome table
- `decoding_results.{csv,json}` – per-read traces
- `ecc_stats.{csv,json}` – aggregated ECC metrics

These files live in the repository root and are git-ignored to keep history clean.

Inspect with any spreadsheet tool or `jq`:

```bash
jq '.ber' ecc_stats.json
```

#### 3.1.1 Hamming32bit1Gb

Simulates a sparse 1 GB memory using SEC-DED Hamming codes.

```
./Hamming32bit1Gb
```

During execution it runs a seven-scenario test suite (no errors, single-bit, double-bit, parity-bit, burst, random multi-error, mixed workload) and reports corrections/detections plus energy estimates.

#### 3.1.2 Hamming64bit128Gb

Extends the model to 64-bit words and a theoretical 128 GB address space. Includes a “Million Word Dataset” stress test and optional `RUN_STRESS_TEST=1` read/write burn-in.

```
./Hamming64bit128Gb
```

Outputs the same `ecc_stats` and `decoding_results` logs as the 32-bit version.

#### 3.1.3 BCH vs Hamming Comparison

```
./BCHvsHamming
```

Runs a side-by-side BCH(63,51,2) vs. SEC-DED Hamming evaluation over multiple error patterns and saves the summary in `comparison_results.*`.

#### 3.1.4 SAT Solver Demo

```
./SATDemo
```

Demonstrates a small DPLL SAT solver used for Hamming-code conjectures, printing solver statistics and example proofs.

### 3.2 Python Utilities

#### 3.2.1 `eccsim.py`

Central CLI exposing reliability, energy and carbon analysis.

- **Reliability report** – computes FIT rates and mean-time-to-failure:

  ```bash
  python eccsim.py reliability report --qcrit 1.2 --qs 0.25 --area 0.08 --flux-rel 1 --json
  ```

  Produces a JSON object (stdout) and a formatted table (stderr) with key metrics like `fit_bit`, `fit_system` and `mttf`.

- **Energy estimation**:

  ```bash
  python eccsim.py energy --code sec-ded --node 16 --vdd 0.7 --temp 25 --ops 1e6 --lifetime-h 1e4
  ```

  Reports dynamic/leakage energy and totals.

- **Carbon footprint**:

  ```bash
  python eccsim.py carbon --areas 0.1,0.2 --alpha 0.5,0.5 --Edyn 1e-15 --Eleak 1e-18 --ci 0.4
  ```

  Prints embodied, operational and total kgCO₂e.

#### 3.2.2 `energy_model.py`

Quick energy-per-read estimator driven by calibration data:

```bash
python3 energy_model.py <parity_bits> [detected_errors]
```

Example:

```
python3 energy_model.py 8 1
```

Outputs a single line like `Estimated energy per read: 2.0e-12 J`.

#### 3.2.3 `ecc_selector.py`

Recommends an ECC scheme given runtime conditions:

```bash
python3 ecc_selector.py <ber> <burst_length> <vdd> <energy_budget> <required_bits> [--sustainability]
```

Example output lists the chosen code, correctable bits, burst tolerance, energy estimate and supported VDD range.

#### 3.2.4 `parse_telemetry.py`

Parses decoder telemetry logs:

```bash
python3 parse_telemetry.py --csv tests/data/sample_secdaec.csv --node 16 --vdd 0.7
```

Reports total energy and per-correction energy; also accessible via `make epc-report` with parameters `CSV`, `NODE` and `VDD`.

---

## 4. Interpreting Structured Results

- **`ecc_stats.*`** – aggregate statistics; field `ber` (bit error rate) illustrates overall reliability and can be queried with `jq` or loaded into pandas.
- **`decoding_results.*`** – per-read logs including addresses, injected errors and correction outcomes; useful for deeper debugging.
- **`comparison_results.*`** – summarises BCH vs. Hamming performance across test cases.

All logs are CSV and JSON so they can be imported into notebooks or spreadsheets for plotting or further analysis.

---

## 5. Testing

1. Install Python dependencies (see §1).
2. Build C++ binaries (`make`).
3. Run the full test suite:

```bash
make test
```

`make test` compiles all simulators, executes a CTest/GoogleTest run and then invokes both shell and Python tests via pytest.

---

## 6. Suggested Workflow for New Users

1. **Clone repository** and install dependencies.
2. **Compile simulators** with `make` or individual `g++` commands.
3. **Run a simulator** (e.g., `Hamming32bit1Gb`) to see statistics and generate log files.
4. **Explore structured logs** with `jq`, pandas or spreadsheets for further insight.
5. **Use Python tools**:
   - `eccsim.py reliability report` for FIT/MTTF calculations.
   - `energy_model.py` for quick energy estimates.
   - `ecc_selector.py` to choose an ECC code for given conditions.
   - `parse_telemetry.py` to analyse energy telemetry.
6. **Run tests** to confirm environment health.

Following these steps a novice can compile, execute and interpret all aspects of the framework.

---

## License

This project is licensed under the [MIT License](LICENSE).

## Comprehensive Analysis

After generating a Pareto frontier with `eccsim select`, additional analysis tools
are available under the new `analyze` command family:

```bash
eccsim select --codes sec-ded,sec-daec --node 7 --vdd 0.8 --temp 25 --capacity-gib 1 --ci 400 --bitcell-um2 0.1 --report pareto.csv

eccsim analyze tradeoffs --from pareto.csv --out reports/tradeoffs.json \
    --bootstrap 20000 --seed 1 --filter "carbon_kg < 2"

eccsim analyze archetype --from pareto.csv --out reports/archetype.json
```

These commands quantify exchange rates on the frontier and attach
high-level archetype labels to each design point.

Energy reports now include an explicit `E_scrub_kWh` column in `pareto.csv`
capturing background scrub energy. JSON summaries set
`"includes_scrub_energy": true` to signal that operational carbon accounts for
these reads.

## Example SKU Studies

Run the helper script to explore multiple reliability scenarios and emit example artifacts:

```bash
bash scripts/run_sku_studies.sh
```

Versioned results for a light MBU rate, CI=0.55 and 5 s scrub interval are provided for reference:

- `reports/examples/sku-64b-128Gb/mbu-light_ci-0.55_scrub-5/`
- `reports/examples/sku-32b-1Gb/mbu-light_ci-0.55_scrub-5/`

Each directory includes `pareto.csv`, `tradeoffs.json`,
`sensitivity-vdd.json` and `archetypes.json`.
