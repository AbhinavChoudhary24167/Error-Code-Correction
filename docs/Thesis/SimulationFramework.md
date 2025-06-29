# Simulation Framework

This draft outlines how each tool supports the broader sustainability study.

## Goals
- Create a repeatable environment for injecting diverse fault types.
- Quantify correction capability and energy overhead across ECC schemes.
- Generate tables and plots for thesis documentation.

## Assumptions
- All simulators share common error injection helpers.
- Memory usage remains sparse regardless of theoretical capacity.
- Energy measurements rely on `energy_model.py` values per operation.

## Role of Each Simulator
- **Hamming32bit1Gb** – unit tests and early debugging of SEC-DED logic.
- **Hamming64bit128Gb** – scalability checks for large memories and workloads.
- **BCHvsHamming** – side-by-side comparison between BCH and Hamming resilience.

Additional simulators may be added later, but these form the starting point for the simulation infrastructure.
