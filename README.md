# Error-Code-Correction
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
