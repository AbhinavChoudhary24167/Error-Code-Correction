# Error-Code-Correction

See [docs/TestSummary.md](docs/TestSummary.md) for an overview of the simulator tests.

ECC for SRAM, studying the impact of ECC architectures on sustainablity

Running the simulators now produces several structured result files in the
repository root:

- `comparison_results.json` – JSON variant of the BCH vs. Hamming results.
- `decoding_results.csv` / `decoding_results.json` – per-read decode logs.
- `ecc_stats.csv` / `ecc_stats.json` – aggregated ECC statistics.

These files are listed in `.gitignore` so that repeated runs do not clutter
your Git history.

Example of inspecting `ecc_stats.json` with `jq`:

```bash
$ jq '.ber' ecc_stats.json
0.000023
```

## Running the BCH vs Hamming comparison

1. Compile the simulator:

   ```bash
   g++ -std=c++11 BCHvsHamming.cpp -o BCHvsHamming
   ```

2. Execute the binary:

   ```bash
   ./BCHvsHamming
   ```

The program prints a detailed report and writes `comparison_results.csv`
to the repository root containing a summary table of each test case.

## Running the 64-bit memory simulator

1. Compile the simulator:

   ```bash
   g++ -std=c++11 Hamming64bit128Gb.cpp -o Hamming64bit128Gb
   ```

2. Execute the binary:

   ```bash
   ./Hamming64bit128Gb
   ```

The built-in test suite now includes a `Million Word Dataset` stress test
which touches one million addresses using the simulator's write and read
operations. After completion, the program prints a short summary of how many
errors were corrected or detected during the test.
It also reports an estimated energy cost for all read operations using
constants derived from recent CMOS literature.

The simulator also provides an optional `One Million Read/Write Stress Test`
that sequentially writes and verifies one million random 64-bit words
without injecting faults. Set the environment variable `RUN_STRESS_TEST=1`
before running the binary to enable this check. It exercises the memory
allocator and decoder under a heavy access workload.

## Running the 32-bit memory simulator

1. Compile the simulator:

   ```bash
   g++ -std=c++11 Hamming32bit1Gb.cpp -o Hamming32bit1Gb
   ```

2. Execute the binary:

   ```bash
   ./Hamming32bit1Gb
   ```

The executable performs a sequence of built-in tests over a small 1 GB memory
space and prints a report summarizing the number of corrected and detected
errors.

## Running the SAT solver demo

1. Compile the solver:

   ```bash
   g++ -std=c++11 SAT.cpp -o SATDemo
   ```

2. Execute the binary:

   ```bash
   ./SATDemo
   ```

The program demonstrates various SAT checks for Hamming code conjectures and
prints solver statistics and example solutions to the console.

## Using the energy model

See [docs/EnergyModel.md](docs/EnergyModel.md) for a detailed explanation of the
`energy_model.py` script. From the repository root you can run:

```bash
python3 energy_model.py <parity_bits> [detected_errors]
```

The script estimates the energy required for a read operation based on the
number of parity bits and detected errors.

## Selecting an ECC scheme at runtime

`ecc_selector.py` chooses the most suitable error-correcting code from a
predefined table. It weighs the bit error rate, burst length, supply voltage,
energy budget per memory access and the minimum number of correctable bits
before suggesting an option.

```bash
python3 ecc_selector.py <ber> <burst_length> <vdd> <energy_budget> <required_bits> [--sustainability]
```

Passing `--sustainability` makes the selector prefer the lowest energy option
that still satisfies all constraints.

### Example

```bash
python3 ecc_selector.py 5e-6 2 0.7 1e-15 2
```

Example output:

```
Selected ECC_Type: TAEC
Code: (75,64)-I6
Correctable bits: 3
Burst tolerance: 3
Estimated energy per read: 9.750e-16 J
Supported VDD range: 0.4-0.8 V
```

These lines indicate the chosen code and its properties, allowing you to verify
that it meets your requirements.

### Parsing telemetry logs

`parse_telemetry.py` processes the decoder telemetry stored in CSV format. Pass
the log file via `--csv` and specify the process node and supply voltage using
`--node` and `--vdd`:

```bash
python3 parse_telemetry.py --csv tests/data/sample_secdaec.csv --node 16 --vdd 0.7
```

The script reports the total energy consumed and the energy required for each
correction in the log.

## Running the tests

Before executing the test suite make sure the Python dependencies are
installed:

```bash
pip install -r requirements.txt
```

Then run the tests using the Makefile:

```bash
make test
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on building the
project with the provided Makefile and running the full test suite.

## License

This project is licensed under the [MIT License](LICENSE).
