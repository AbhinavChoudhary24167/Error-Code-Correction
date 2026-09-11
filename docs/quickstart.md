# Quickstart

Run all commands from the repository root.

## Five-minute reviewer smoke test

Prerequisite: Python dependencies from `requirements.txt` and GNU Make.

```bash
make reviewer-smoke
```

Expected output: an artifact-integrity pass marker, JSON verification output for `hsiao-generated-combinational-72-64-v1`, a seeded SRAM simulation JSON object, and a pytest pass summary. Output is written to stdout; the workflow does not create a campaign.

Common failures: missing Python packages, an interpreter different from the one used to install dependencies, a damaged manifest, or a broken documentation link. Run `python eccsim.py doctor --json` and consult [Troubleshooting](TROUBLESHOOTING.md).

## One ECC verification

```bash
python eccsim.py ecc verify --implementation hsiao-generated-combinational-72-64-v1
```

Expected output: a JSON report naming the implementation, declared verification universe, result counts, evidence, and status. This verifies the registered software/RTL-bound policy; it is not a physical, radiation, or silicon test.

## One seeded SRAM simulation

```bash
python eccsim.py sram simulate --size-kb 64 --word-bits 8 --scheme sec-ded --iterations 100 --seed 17 --json
```

Expected output: JSON summary on stdout. Change only supported choices listed by `python eccsim.py sram simulate --help`. The seed makes the pseudorandom sequence reproducible for the same software/environment; it does not make a Monte Carlo estimate universally exact.

## Full local validation

Prerequisites: a C++17 compiler and GNU Make in addition to Python packages.

```bash
make
make test
python -m pytest -q
```

Native binaries and dependency files are local build products. `make clean` removes only those products; it never removes `campaigns/`, `results/`, or `reports/` evidence.
