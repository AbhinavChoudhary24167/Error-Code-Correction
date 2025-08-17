# Energy Model

This module provides a tiny energy estimation for each read operation in the
simulators. It multiplies the number of XOR and AND gate evaluations by
technology-aware energy costs loaded from `tech_calib.json`.

## Calibration

`tech_calib.json` maps process node and voltage to per-gate energy figures for
XOR and AND operations. The loader performs piecewise linear interpolation over
this table so the estimate reflects the chosen technology and supply voltage.

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

## Typical Values from Literature

The calibration data includes energy measurements published for 28&nbsp;nm CMOS
processes, where an XOR gate consumes roughly 2&nbsp;pJ per operation and an AND
gate about 1&nbsp;pJ. These figures provide a reasonable baseline when evaluating
the simulators on common hardware.
