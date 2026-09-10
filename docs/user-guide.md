# User guide

All commands below run from the repository root.

## A. Inspect the environment

`python eccsim.py doctor --json` reports Python packages and external tools. Add `--strict` when a nonzero status is required for missing required components.

## B. Explore registered ECCs

```bash
python eccsim.py ecc list
python eccsim.py ecc verify --implementation hsiao-generated-combinational-72-64-v1
```

Use the exact implementation ID printed by `ecc list`. `--out FILE` writes a verification report.

## C. Run a seeded SRAM simulation

```bash
python eccsim.py sram simulate --size-kb 64 --word-bits 8 --scheme sec-ded --iterations 1000 --seed 17 --json
```

Allowed sizes are 64/128/256 KiB, word widths 8/16/32, and schemes `sec-ded`, `taec`, `bch`, or `polar`. Use `--out-csv FILE` for CSV. The model/fault-model name and seed belong with the result.

## D. Produce a reliability model report

```bash
python eccsim.py reliability report --qs 1e-15 --area 1e-6 --node-nm 14 --vdd 0.8 --tempC 75 --json
```

Qcrit, flux, area, altitude, capacity basis, MBU preset, and scrub interval are assumptions unless a bound evidence record says otherwise. This command does not create physical FIT evidence.

## E. Compare configurations

```bash
python eccsim.py compare --input-config configs/example_config.json --outdir output/comparison
```

Start from a maintained JSON under `configs/`; validate the produced manifest and null fields. Do not compare records with different functional units or physical boundaries.

## F. Validate the artifact

```bash
make artifact-check
make docs-check
```

These are read-only integrity checks and do not rerun experiments.

## G. Build and test

```bash
make
make test
python -m pytest -q
```

Native build outputs are local and ignored. Remove them with `make clean`.

## H. Rebuild registry documentation

```bash
make reproduce
```

Review all diffs. This regenerates the established registry study; it does not rewrite frozen physical campaign evidence.

## I. Interpret results

Check the code/implementation/architecture IDs, units, workload, fault population, technology/PVT, seed, boundary, evidence tier, qualification status, and forbidden uses. Null means unknown or unqualified, never zero. See [Results schema](results-schema.md).

## J. Extend the work

Follow [Adding an ECC](adding-an-ecc.md) or [Adding an experiment](adding-an-experiment.md). New work is additive and receives new IDs; existing selector behavior and output fields stay compatible.
