# Troubleshooting

## `doctor` reports a Windows C++ runtime mismatch

Multiple applications may provide `libstdc++-6.dll`. Put the `bin` directory belonging to the selected `g++` first on `PATH`, open a new shell, and rerun `python eccsim.py doctor --strict`. Do not copy DLLs into the repository.

## `python3 -m pytest` differs from `python -m pytest`

On Windows/MSYS2, those commands can select different interpreters. Compare `python --version`, `python3 --version`, and their executable paths. Install requirements into the interpreter required by the command, or activate one virtual environment consistently.

## Native build output appears in Git status

Current root binaries, `.exe`, `.o`, and `.d` files are ignored. Run `make clean`. Executables inside frozen campaign integrity directories may be historical evidence and must not be removed wholesale.

## A documentation link or artifact check fails

Run `python scripts/check_artifact.py` for the exact error. Fix the referenced path or contract. Do not weaken a guard merely to make a changed scientific claim pass.

## Verification produces a counterexample

Treat it as evidence. Preserve the inputs, implementation ID, mask, observed outcome, and report. Exclude the implementation only from uses whose functional gate failed; do not delete the record.

## A physical run completed but timing failed

This is a completed flow and a timing-infeasible implementation at that constraint. Do not call it timing closure or discard it. Inspect the campaign timing summary and matched controls.

## OpenRAM output is incomplete

The retained 256×72 attempt timed out after 10,800 seconds. Logs/geometry do not imply LEF, Liberty, SPICE, Verilog, DRC, LVS, or characterization. A new attempt needs a new output root and campaign record.

## Hashes change on Windows

Campaign text uses LF attributes to prevent line-ending damage. Do not run bulk normalization over frozen evidence. Restore unintended changes, identify the exact byte source, and use a documented scientific-hash migration only when scientifically necessary.
