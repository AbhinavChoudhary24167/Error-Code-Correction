# Release Signoff Checklist

The release signoff package must be built under:

- `reports/signoff/<version>/`

Use `scripts/build_signoff_package.py` to assemble and validate the package.

## Mandatory artifacts

1. `calibration_envelope.md`
   - Defines the calibrated validity region (node, VDD, temperature, process corner).
2. `provenance_manifest.json`
   - Captures data lineage and source traceability.
3. `uncertainty_report.json`
   - Documents uncertainty bounds used for risk-aware interpretation.
4. `holdout_metrics.json`
   - Contains holdout evaluation metrics and threshold pass/fail status.
5. `drift_status.json`
   - Reports drift severity or drift-policy action for current data.
6. `compatibility_test_results.json`
   - Summarizes backward-compatibility test outcomes.
7. `summary.md`
   - One-page executive summary in plain language for reviewers.

## Release gate expectations

A release is blocked when any of the following is true:

- A mandatory artifact is missing.
- Holdout metrics thresholds fail (`signoff.pass` or `thresholds_pass` is false).
- Drift status indicates a fail condition (policy `action == "fail"` or severity `high`).
- Compatibility results indicate failure (`pass == false` or `failed > 0`).

## CI usage

The GitHub release workflow runs:

- `scripts/build_signoff_package.py`

The command exits non-zero on any missing artifact or failed threshold, which blocks the release.
