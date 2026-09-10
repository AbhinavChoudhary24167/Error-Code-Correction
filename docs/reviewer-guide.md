# Reviewer guide

This path checks the claims most likely to affect interpretation in about 10–20 minutes on a prepared software environment.

## 1. Establish identity and health

```bash
git rev-parse HEAD
python eccsim.py --version
python eccsim.py doctor --json
```

The doctor is descriptive unless `--strict` is supplied. Record optional-tool and compiler-runtime findings rather than treating them as scientific results.

## 2. Run the deterministic smoke contract

```bash
make reviewer-smoke
```

This validates required files, JSON/CSV structure, guard fields, local documentation links, one registered Hsiao implementation, a seeded 64 KiB SRAM run, and representative Python tests.

## 3. Inspect the evidence boundary

```bash
python eccsim.py ecc list
python eccsim.py ecc verify --implementation hsiao-generated-combinational-72-64-v1
```

Then read the [v3.3 campaign status](../campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/CAMPAIGN_STATUS.json), [matched physical report](../campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation/FINAL_REPORT.md), and [OpenRAM provenance](../campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation/OPENRAM_PROVENANCE.json).

Confirm that:

- `global_winner` is `NO_GLOBAL_WINNER_QUALIFIED`;
- `whole_memory_e5_qualified` is false;
- the runtime budget scope is `ENTIRE_CAMPAIGN` and 54,000 seconds;
- the OpenRAM fresh run is `TIMEOUT`, not completed;
- SEC-DAEC's failed counterexample remains preserved.

## 4. Optional full software contract

```bash
make
make test
python -m pytest -q
```

## What this does not reproduce

The short path does not rerun OpenROAD, regenerate OpenRAM, establish physical FIT/Qcrit, measure silicon, or qualify SKY130 lifecycle carbon. Large GDS and campaign logs are retained evidence, not prerequisites for the smoke test.
