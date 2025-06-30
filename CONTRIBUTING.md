# Contributing

Thank you for taking the time to contribute to this project!

## Building the project

All C++ sources can be compiled at once using the provided Makefile:

```bash
make
```

This produces the following binaries in the repository root:
`BCHvsHamming`, `Hamming32bit1Gb`, `Hamming64bit128Gb`, and `SATDemo`.

## Running smoke tests

A small smoke test is available to ensure the binaries start up correctly.
After building the project simply run:

```bash
make test
```

The `test` target invokes `tests/smoke_test.sh` which runs each binary
with a 5‑second timeout. If all programs exit successfully the script
prints `All smoke tests passed.`.
