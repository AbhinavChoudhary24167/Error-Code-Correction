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

## License

This project is licensed under the [MIT License](LICENSE).
