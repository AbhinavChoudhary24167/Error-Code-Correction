# Attempt10: GREEN Matrix Physical-Model Validation

This campaign extends the frozen Attempt09 SRAM/ECC evidence into an auditable physical-to-sustainability evidence chain. It does not alter Attempt09, production Liberty, SRAM internals, Gate-3 constraints, default CLI behavior, or the deterministic ECC selector. Historical Gate-3 remains **FAIL** with `RESIDUAL_SRAM_INPUT_DRV_FAIL`; the recommended reassessment remains `KEEP_GATE3_FAILED`.

## Outcome

The campaign classification is `EVIDENCE_CHAIN_ESTABLISHED_SELECTION_NOT_QUALIFIED`. It creates the full GREEN schema and scenario infrastructure while withholding energy, physical reliability, carbon, normalized scores, and Pareto winners whose inputs are not qualified.

The Liberty audit proves that SRAM22's global `default_max_transition : 0.04` conflicts with all 24 supplied output transition tables across six frozen views. Thirty strict OpenROAD runs were executed. All ten original runs completed and reproduce Attempt09. All ten diagnostic E0 runs completed; research-corrected and no-global E0 results are identical. Their five-seed mean changes versus original are -6.7524% standard-cell area, +0.7381% wirelength, -7.5332% vias, and -0.5083% comparative tool power. All ten diagnostic U0 runs abort deterministically at global placement with `RSZ-0090`, so corrected U0 PPA is `NOT_MEASURED`. This is material optimizer behavior, not merely warning reclassification, and neither diagnostic view is foundry-qualified.

The rstb study classifies the 256x64 limitation as `INSUFFICIENT_EVIDENCE`. Its rise pin capacitance is 0.448008 pF versus 0.250926 pF for 256x8 (1.785419x); pin load dominates routed wire capacitance. Even zero-wire and local strongest-driver controls miss 0.351 ns on 256x64, while the ECC 256x8 interface can pass. The evidence does not prove a universal interface limitation or invalidate the Liberty constraint.

Eight matched RTL workloads run for U0/E0 with checked outputs and no unknowns. A seed-11 upstream-original post-route diagnostic annotates 48.68% of U0 pins and 4.35% of E0 pins. Its tool estimates remain diagnostic because it lacks mapped glitch activity, five-seed/model coverage, validated macro internal power, and disjoint component attribution. All energy-per-access values remain `NOT_QUALIFIED`.

I0 macro placement is physically evidenced. I1/I2 interleaving are explicit implementation proposals; no bitcell/address map or implementation cost exists yet. Logical SECDED controls are exact, but physical SER/FIT/SDC/DUE and interleaving coverage remain `NOT_QUALIFIED`. Carbon equations and scenario inputs are documented, but all totals remain gated. The raw GREEN matrix contains 5,760 rows; zero rows qualify for normalization or Pareto analysis.

## Evidence map

- Liberty audit and sensitivity: `liberty/`
- Rstb characterization: `rstb/`
- Physical, reliability, raw, and normalized GREEN data: `green_matrix/`
- Activity and energy evidence: `energy/`
- Physical topology and interleaving proposals: `interleaving/`
- Carbon model and blocked results: `carbon/`
- Pareto eligibility and analysis: `pareto/`
- Baseline/final integrity, external evidence hashes, and regressions: `integrity/`
- Raw ORFS evidence: `/var/tmp/green-ecc-attempt10/orfs` in WSL; every file is hashed by `integrity/external_raw_manifest.json`.

## Reproduction

Run campaign-local validation:

```powershell
python -m pytest -q campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation/tests
python campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation/scripts/build_green_analysis.py
```

The full OpenROAD matrix is defined by `scripts/run_liberty_sensitivity.sh`; it requires the frozen Docker image `sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e` and the frozen Attempt09 sources. The Windows workspace had insufficient free space for 5.6 GiB of raw results, so runs were retained in WSL ext4 and structured outputs were written here.

Repository-required regression commands and their exact outcomes are recorded in `integrity/REGRESSION_STATUS.json` and `integrity/regression/`. Machine-readable per-phase answers to all 15 required summary questions are in `CAMPAIGN_STATUS.json`.
