# Cleanup diff summary

## Outcome

Phase 0 removed 146 known disposable targets: untracked bytecode/pytest caches, untracked UUID test workspaces, and ordinary compiler/executable intermediates. Two OneDrive cache directories required exact-path revalidation and elevated removal after normal deletion was denied. `PracticalSRAMSimulator.exe` was excluded from cleanup, changed during the required build, and restored byte-for-byte to SHA-256 `99fbb17b7a9bc4296d6a044e5edc496f131def71e532062b563a776ab31e06ef`.

The first deletion pass exposed a classification defect: 120 UUID-named ML workspaces were generated-looking but tracked. They were immediately restored from parent commit `9968f9b15f949d38faf944a3546ea736cfab63df`, before any commit, and the audit now enforces `TRACKED_IMPLIES_KEEP_SOURCE_OF_RECORD`. Final tracked-worktree diff after restoration is empty outside this new campaign.

No item was accepted as `DEAD_CODE`. Seven ambiguous root outputs remain `UNKNOWN_REQUIRES_RETENTION`; five legacy calibration inputs remain `KEEP_SOURCE_OF_RECORD`.

## Preserved evidence

- Attempt09 tree: 2,098 files, 5,132,662,262 bytes, SHA-256 tree fingerprint `146242fee8690f23434198d0a1f6cd22267bbbf357461e797c75f4c614cc77ac` before and after cleanup.
- Attempt10 tree: 302 files, 51,428,283 bytes, SHA-256 tree fingerprint `5d0ca45b8c14f9d6ac6ce810562f6d3d782e4d96e7c6dc6e35c19f47e13b3b33` before and after cleanup.
- all 565 baseline tracked-source hashes match;
- all 7 baseline calibration hashes match;
- `git diff HEAD -- docs/date2027 paper/date2027_revision3` is empty;
- the frozen SRAM22 commit, Liberty hashes, PDK limitation, and standard-cell Liberty identity remain exactly as recorded in `CAMPAIGN_BASELINE.json`.

Thus cleanup changed no historical result or source input.

## Regression result

- campaign-local historical suites: 49 passed;
- `make`: passed;
- `make test`: 482 passed, 2 failed;
- `python3 -m pytest -q`: 484 passed, 2 failed.

Both full-suite failures are the exact frozen validators recorded by Attempt10:

- `tests/python/test_gate03_artifacts.py::test_gate01_gate02_immutable_authorized_scope_and_binary_verdict`
- `tests/python/test_gate03e_artifacts.py::test_gate03e_artifact_validator`

They reject the already-untracked `campaigns/iscas_sustainability_extension` working-tree scope. There are no new failure node IDs and no product-test regression. Full logs and hashes are in `integrity/regression/`.
