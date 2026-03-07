# Signoff Input Artifacts

This directory is the default input location for the release signoff gate workflow.

Expected files:

- `holdout_metrics.json`
- `drift_status.json`
- `compatibility_test_results.json`

These files are consumed by `scripts/build_signoff_package.py` and copied into
`reports/signoff/<version>/` during release gating.
