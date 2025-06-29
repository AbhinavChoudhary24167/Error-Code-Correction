# Energy Model

This module provides a tiny energy estimation for each read operation in the
simulators. It multiplies the number of XOR and AND gate evaluations by
constant energy costs.

## Constants

- `ENERGY_PER_XOR` – energy in joules used by a single XOR gate. The default
  value is `2e-12` J.
- `ENERGY_PER_AND` – energy in joules used by a single AND gate. The default
  value is `1e-12` J.

## Running the script

1. From the repository root, run the module with the number of parity bits and
   optionally the detected error count:

   ```bash
   python3 energy_model.py <parity_bits> [detected_errors]
   ```

   Example:

   ```bash
   python3 energy_model.py 8 1
   ```

   The command above estimates the energy to process eight parity bits when one
   error was detected.

2. The script prints a single line:

   ```
   Estimated energy per read: <value> J
   ```

   `<value>` is the estimated energy in joules, formatted in scientific notation.

This simple calculation helps gauge the energy impact of different error control
coding schemes during reads without running the full simulators.
