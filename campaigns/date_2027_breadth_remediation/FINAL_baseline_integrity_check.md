# Final Revision-2 baseline integrity check

## Frozen baseline

- Baseline commit: `b51291442bbd04346dac939dea6ba7d532b9c5c4`
- Baseline branch: `main`
- Additive campaign branch: `codex/date-2027-breadth-remediation`
- Inventory: `00_baseline_inventory.sha256`
- Algorithm: SHA-256 over raw file bytes
- Protected repository files: 79
- Protected external Revision-2 files: 2,366
- Total protected files: 2,445

The final verification found zero changed paths, zero missing paths, and zero added paths within the frozen protected scopes. This includes all tracked Revision-2 evidence and manuscript sources, the eight protected qualified RTL/boundary identities, and every file in `/var/lib/green-ecc-date2027-revision2`.

`HISTORICAL_REV2_INTEGRITY = PASS`

The machine-readable verification record is `FINAL_baseline_integrity_check.json`.

## Before/after repository tests

| Check | Stage-0 result | Final result |
|---|---:|---:|
| `make` | PASS | PASS |
| `make test` | 484 passed, 0 failed, 0 skipped, 3 warnings | 484 passed, 0 failed, 0 skipped, 3 warnings |
| `python3 -m pytest -q` | 486 passed, 0 failed, 0 skipped | 486 passed, 0 failed, 0 skipped |
| Campaign-local evidence contracts | not present at Stage 0 | 7 passed, 0 failed, 0 skipped |

The first post-campaign `make test` diagnostic run reported two legacy working-tree scope-guard failures because the new `campaigns/date_2027_breadth_remediation/` namespace was not in the historical Gate-03/03E allowlists. No functional test failed. A minimal additive allowlist entry was added to `scripts/gate03e/validate_artifacts.py` and its mirror assertion in `tests/python/test_gate03_artifacts.py`; the two focused tests then passed, and both mandated full suites passed at their unchanged baseline counts. This intermediate diagnostic result is retained here rather than hidden.

The final test runs rebuilt `PracticalSRAMSimulator.exe` and created twelve UUID-named runtime fixture directories. The binary was restored to exact HEAD bytes and only those twelve verified test-created directories were removed. No pre-existing user path was removed.
