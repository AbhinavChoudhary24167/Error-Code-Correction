# Contributing

Thank you for taking the time to contribute to this project!

## Building the project

All C++ sources can be compiled at once using the provided Makefile:

```bash
make
```

This produces the following binaries in the repository root:
`BCHvsHamming`, `Hamming32bit1Gb`, `Hamming64bit128Gb`, and `SATDemo`.

## Running tests

The project includes a small smoke test as well as a GoogleTest based unit
test. Both are executed via the Makefile:

```bash
make test
```

The `test` rule first builds and runs the unit tests using CMake's `ctest`
(via the `gtest` target) and then executes `tests/smoke_test.sh`. If all
programs exit successfully the script prints `All smoke tests passed.`.
