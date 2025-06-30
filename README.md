# Error-Code-Correction

See [docs/TestSummary.md](docs/TestSummary.md) for an overview of the simulator tests.

ECC for SRAM, studying the impact of ECC architectures on sustainablity

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

The repository includes a small utility named `ecc_selector.py` which chooses
an appropriate ECC configuration given several runtime constraints. Provide the
bit error rate, expected burst length, supply voltage, energy budget per
memory access and the minimum number of correctable bits:

```bash
python3 ecc_selector.py <ber> <burst_length> <vdd> <energy_budget> <required_bits> [--sustainability]
```

Passing `--sustainability` makes the selector prefer the lowest energy option
that still satisfies all constraints.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on building the
project with the provided Makefile and running the smoke test suite.

## License

This project is licensed under the [MIT License](LICENSE).
