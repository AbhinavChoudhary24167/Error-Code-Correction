# Simulator Overview

This document explains the purpose and usage of each simulator in the repository. It consolidates information from the README and source comments so that new contributors can quickly understand the available tools.

## Table of Contents
- [Hamming32bit1Gb](#hamming32bit1gb)
- [Hamming64bit128Gb](#hamming64bit128gb)
- [BCHvsHamming](#bchvshamming)
- [SATDemo](#satdemo)
- [Common Features](#common-features)

## Hamming32bit1Gb
`Hamming32bit1Gb.cpp` implements a SEC‑DED memory simulator for 32‑bit words. It allocates memory sparsely using a hash map so the theoretical 1&nbsp;GB capacity does not require gigabytes of RAM. The simulator offers several helper methods for fault injection:

- `injectError(address, bit_position)` – flip a single bit within a stored codeword.
- `injectBurstError(address, start, length)` – flip `length` adjacent bits.
- `injectRandomErrors(address, count)` – flip `count` random bit positions.

The main program runs a suite of tests ranging from simple single bit flips to large mixed workloads. After execution it prints a formatted statistics summary and writes structured logs (`ecc_stats.json` and `ecc_stats.csv`).

## Hamming64bit128Gb
`Hamming64bit128Gb.cpp` scales the SEC‑DED approach to 64‑bit words and a theoretical 128&nbsp;GB address space. The code structure mirrors the 32‑bit version but uses a standard map to hold only addresses that are actually written. It includes additional tests such as a large address space demonstration and a "Million Word Dataset" stress test.

## BCHvsHamming
`BCHvsHamming.cpp` provides a side‑by‑side comparison of a BCH(63,51,2) decoder with the custom SEC‑DED Hamming implementation. It runs a number of scenarios (no errors, single, double and triple bit flips, random patterns) and reports which code successfully corrected the data. A CSV/JSON summary is produced in `comparison_results.*`.

The BCH path is powered by the reusable codec in [`src/bch63.hpp`](../src/bch63.hpp), which constructs GF(2^6) with the primitive polynomial x^6 + x + 1, derives the generator polynomial as the least common multiple of the minimal polynomials of α and α^3, and performs systematic encoding via polynomial division. Decoding implements Berlekamp–Massey to synthesise the error locator followed by a Chien search to find error positions, matching the double-error-correcting design described in Lin and Costello’s *Error Control Coding* (2nd ed., §6.3). Exhaustive unit tests in `tests/unit/BCH63_test.cpp` confirm that every single- and double-bit error is corrected and every weight-3 error pattern is detected.

## SATDemo
`SAT.cpp` contains an educational SAT solver used to prove small Hamming‑code properties. The solver implements a basic DPLL procedure with VSIDS‑like heuristics. Example routines encode conjectures about Hamming codes and demonstrate satisfiability or contradictions.

## Common Features
All simulators rely on shared concepts:

- Sparse memory models so that only touched addresses consume RAM.
- Fault injection helpers used by the automated test suites.
- Optional structured logging to JSON and CSV files for later analysis.

## CSV Output Files

Several components emit comma‑separated values that can be imported into
spreadsheet tools or pandas for further analysis:

- The Hamming simulators write aggregated metrics to `ecc_stats.csv` and
  per‑read traces to `decoding_results.csv` using `std::ofstream` streams in
  their source code. [`Hamming32bit1Gb.cpp`](../Hamming32bit1Gb.cpp) and
  [`Hamming64bit128Gb.cpp`](../Hamming64bit128Gb.cpp) contain the relevant
  logging calls.
- `BCHvsHamming.cpp` saves the outcome of its test scenarios to
  `comparison_results.csv`.
- `parse_telemetry.py` validates raw telemetry logs against the schema in
  `docs/schema/telemetry.schema.json` and writes a normalised CSV via
  `pandas.DataFrame.to_csv`.
- Analysis utilities such as `plot_pareto.py` export their results to CSV (for
  example, `pareto.csv`) for downstream processing.

The `energy_model.py` script estimates the energy cost of a read operation based on the number of evaluated parity bits and detected errors. `ecc_selector.py` recommends an ECC scheme given runtime conditions such as bit error rate and energy budget.

