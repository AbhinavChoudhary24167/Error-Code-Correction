# Phase 0 cleanup plan

## Scope and decision rule

The inventory treats a path as a cleanup candidate only when it matches a concrete cache, generated-build, test-workspace, historical-evidence, protected-publication, calibration-source, or unresolved-output rule in `scripts/phase0_audit.py`. Size, age, and byte equality are not deletion evidence.

Deletion is allowed only when all of the following hold:

1. the item is classified `CACHE_TEMPORARY` or `GENERATED_REBUILDABLE`;
2. an explicit regeneration path is recorded;
3. it is outside all prior ISCAS campaign, Attempt01-Attempt10, and protected DATE paths;
4. it is not the protected `PracticalSRAMSimulator.exe`;
5. it is inside the resolved repository root.

The first discovery pass identified 252 cache/test-workspace items and 14 compiler-generated items. A tracked-status review then found that 120 generated-looking UUID workspaces were tracked repository fixtures. They were restored from the unchanged parent before commit and the rule was strengthened to `TRACKED_IMPLIES_KEEP_SOURCE_OF_RECORD`. The final inventory therefore retains 125 source-of-record items, 9 historical campaign roots (10,885,871,691 bytes), 3 protected roots/items (60,971,508 bytes), and 7 unresolved artifacts. The machine-readable inventory reflects the corrected classifications.

## Evidence used

Dead-code and generated-artifact decisions used multiple checks:

- Python imports and module entrypoints were searched across tracked and local campaign sources.
- Script invocation, Makefile targets, CLI entrypoints, tests, CI configuration, documentation, campaign builders, manifests, and dynamic/runtime fixture paths were inspected.
- `tests/python/test_ml_feature_pack.py::_new_base` proves that new UUID-named runtime workspaces are generated for every test invocation; tracked UUID workspaces are nevertheless retained as repository sources of record.
- the Makefile proves regeneration of root object, dependency, and ordinary executable products;
- `.gitignore`, `pytest.ini`, and the Gate03ES scope test independently identify bytecode, pytest caches, and runtime ML fixtures as non-source products;
- historical status and artifact manifests prove that raw failed runs, logs, SRAM22 assets, and regression evidence remain scientifically relevant.

No Python function, class, module, or shell utility met the standard for `DEAD_CODE`: absence of a simple import was not accepted when CLI, dynamic dispatch, campaign reproduction, or historical manifests could still provide a use. Suspected exploratory root outputs remain `UNKNOWN_REQUIRES_RETENTION`.

## Duplicate audit

Exact duplicates are grouped by SHA-256 in `DUPLICATE_FILE_GROUPS.json`. The corrected scan found 676 content-hash groups among candidate roots. Most are intentional historical snapshots or repeated ORFS stage artifacts. They remain category B (`identical historical snapshots retained intentionally`), not redundant deletion targets. Cache/build duplicates are removed only because their regeneration evidence is independently sufficient; equality alone does not authorize deletion.

## OneDrive hash limitation

One stale bytecode file and two `.pytest_cache` members denied content reads through the OneDrive filesystem. Their enclosing directory hashes are marked `PARTIAL_METADATA_UNREADABLE_MEMBER`; they remain cache-class deletion candidates based on independent path, test, and ignore evidence. No source, calibration, protected, or historical evidence hash is partial.

## Execution and validation

After the cleanup action:

1. record every removed target with its pre-deletion size and hash in `DELETED_FILES_MANIFEST.json`;
2. record protected/source/historical decisions in `KEPT_EVIDENCE_MANIFEST.json`;
3. run campaign-local tests, `make`, `make test`, and `python3 -m pytest -q`;
4. restore the exact protected simulator executable bytes if the build changes them;
5. compare Attempt09, Attempt10, protected DATE, SRAM22, tracked-source, and calibration hashes with the baseline;
6. remove only newly regenerated disposable cache/intermediate products after validation and report that post-test housekeeping separately.

Scientific methodology changes are excluded from the cleanup commit.
