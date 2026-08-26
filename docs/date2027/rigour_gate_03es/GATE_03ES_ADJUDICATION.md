# Gate 03E-S read-only adjudication

This record is additive. It does not alter the frozen Gate 03E-S comparison, acceptance record, policy, or failed formal verdict. It supersedes only the contradictory interpretation in the generated report.

## Corrected separation

| Axis | Frozen result | Adjudicated result |
|---|---:|---:|
| Repository commands (`make`, tests, focused and historical suites, `git diff --check`) | Presented as FAIL after being combined with scope | **PASS** |
| Original frozen path-scope validation | FAIL | **FAIL, preserved** |
| Isolated LF candidate-delta scope validation | Not performed | **PASS** |
| Historical evidence bytes | Presented as CHANGED after being combined with scope | **UNCHANGED** |
| Scientific repeatability | Subchecks passed but formal comparison failed | **PASS** |
| Frozen formal contract | FAIL | **FAIL, preserved** |

Post-adjudication repository verification also passed: `make`, `make test` (423 tests), the standalone `python3 -m pytest -q` suite (425 tests), and six focused adjudication tests.

## Ordered duplicate-key adjudication

The preserved 16 JSON log artifacts were parsed as ordered key occurrences; no key was collapsed. The adjudicator compared 2,645 leaf occurrences, including 2,220 duplicate-key occurrences and 556 duplicate scientific occurrences. There were zero scientific failures and zero unresolved occurrences.

The differing raw content is one artifact, `logs/sky130hd/gcd/base/5_1_grt.json`, but it is not one scalar value. It contains 1,138 differing occurrences across nine FastRoute `_s` timer fields. Every difference is classified by the frozen producer catalogue as `RUNTIME_RESOURCE_OBSERVATION`; no scientific or technology value differs.

## Historical byte adjudication

The audit bypassed working-tree status and filters:

- All 384 protected tracked files have identical HEAD and index Git blob identities.
- Current raw protected-tree SHA-256 aggregates match every recorded Gate 03E-S starting value.
- Of those files, 226 working files equal their Git blob bytes directly; the other 158 differ only by CRLF checkout conversion. Normalizing CRLF to LF reproduces the Git blob exactly in all 158 cases. There are zero non-EOL working/blob differences.
- The pre-existing untracked Gate 03E-R evidence tree and both preserved external Gate 03E/Gate 03E-R trees match their recorded SHA-256 values.

Historical evidence is therefore `UNCHANGED`.

## Isolated LF scope adjudication

A disposable checkout of the unchanged starting HEAD was configured with `core.autocrlf=false` and `core.eol=lf`. Only the two authorized compatibility edits, the pre-existing Gate 03E-R delta, and additive Gate 03E-S paths were copied. The frozen scope validator passed all 70 candidate paths. Build and test products were excluded because they are execution outputs, not source-delta candidates. The disposable checkout was removed; no physical flow was run.

## Control decision

No GCD runs 7–8 were performed. Gate 04 was not started and is not authorized by this adjudication. Proceeding requires an explicit superseding authorization that acknowledges the preserved formal failure and accepts this independent scientific adjudication as the basis for Gate 04 entry.

Adjudicated verdict: `SCIENTIFIC_ENVIRONMENT_READY_FORMAL_GATE_FAILED`
