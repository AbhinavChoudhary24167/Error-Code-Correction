# Experiment pipeline

## Stage contract

```text
specification
  -> functional verification
  -> physical/analytical execution
  -> raw evidence retention
  -> normalization
  -> qualification
  -> scenario translation
  -> multi-objective analysis
  -> report + provenance seal
```

Every stage has an input boundary, output boundary, validation condition, and failure state. Downstream work may proceed for unaffected quantities, but it may not silently fill a failed prerequisite.

## 1. Specification

Code and implementation identities live under `green_ecc_physical_simulation/registry/`. General experiment examples live in `configs/`. Campaigns add frozen configurations beside their evidence. Record payload/codeword widths, correction and detection claims, workload, seed, tool context, and intended evidence level before execution.

## 2. Functional verification

`green_ecc_phy/verification.py` and campaign-specific RTL testbenches compare decoded data with golden data and preserve counterexamples. A native decoder flag is not accepted as proof of correctness. The matched campaign's functional summary is `campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation/FUNCTIONAL_VALIDATION_SUMMARY.json`.

## 3. Execution

- Logical/analytical studies run through `eccsim.py` or scripts under `scripts/`.
- Physical runs use the campaign's frozen ORFS configuration and external execution environment.
- v3.3 activity runs use routed-netlist VCD, final SPEF, deterministic warm-up/operation windows, and explicit annotation coverage.

Physical campaigns can require hours and substantial storage. Exact resource needs depend on retained OpenROAD products and parallelism; no universal runtime/disk estimate is asserted. The v3.3 controller had one 54,000-second campaign budget shared across the entire queue, not one budget per subprocess.

## 4. Raw evidence retention

Keep logs, failed attempts, tool reports, configuration snapshots, workload/activity files, and hashes. External large evidence roots are referenced by manifests when not all data are committed. Never overwrite a failed attempt with a later retry; assign a new attempt or campaign identity.

## 5. Normalization and qualification

Normalize numeric values with unit, source type, boundary, technology/PVT, workload, seed, uncertainty, evidence tier, allowed uses, forbidden uses, and dependency hashes. Store unavailable values as null/blocker states. `M_E`, `M_P`, and `M_S` are described in [Results schema](results-schema.md).

## 6. Analysis

Apply functional and fairness filters, then hard constraints, then objective completeness, then Pareto/deterministic policy. Keep rejected and infeasible rows for audit. Report partial fronts by their actual boundary; the v3.3 two-architecture logic-only front is not a global sustainability front.

## 7. Validation and export

Run the campaign's builder/validator, `make artifact-check`, relevant tests, and hash checks. Export CSV for tabular audit and JSON for nested provenance. Figures must identify their source data and generator. A report should link back to the exact manifest and status record.

## Checkpoint and restart behavior

Reusable software commands may write a new output directory. Campaign controllers define their own restart policy. The completed v3.3 queue persisted `RUNTIME_STATE.json`; resumes reused the original deadline. Its README explicitly says not to rerun the expired queue as a new campaign.
