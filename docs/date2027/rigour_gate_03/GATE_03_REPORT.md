# GREEN-ECC DATE 2027 Publication-Rigour Gate 03

## Binary result

`NO_GO_FOR_DATE_2027_REGULAR_PAPER_CORE`

The exact physical-feasible set is empty. Conventional SECDED and Hsiao passed two local verification-stress simulations but did not complete a pinned characterized common flow. Technology mapping to SKY130HD, STA, activity-based power, placement, routing, extraction, post-route analysis, and physical reproducibility are unresolved.

## Mechanical blockers

1. H2 is `UNTESTABLE_IDENTITY_MISMATCH`: conventional is `extended-hamming-secded-72-64-v1` (`40bc866e…`) while Hsiao is `hsiao-secded-72-64-v1` (`1cc658a0…`). Equal dimensions or protection class do not merge identities.
2. BCH is `BLOCKED_MISSING_VALID_RTL`. No pre-existing `(78,64)` source has formal equivalence or the required exact linear-code proof. The decoder requirement is symbolic payload data across all 3,082 weight-0/1/2 masks; probe-only evidence is incomplete.
3. The pinned ORFS image digest, its matching source commit/configuration, and characterized SKY130HD collateral could not be established because WSL2/Docker provisioning was not authorized during the local audit. No mutable checkout was combined with an independently pinned image.

Negative slack did not trigger this decision because no characterized timing run occurred. Storage and total-system energy remain unsupported. The next authorized activity is Gate 03R, followed by a complete two-run Gate-03 re-entry.

## Repository validation

The isolated staged snapshot passed `make`, `git diff --check`, the final staged diff check, and 11 focused Gate-03 tests. `make test` completed with 367 passed and one unrelated pre-existing fixture-hash failure; `python3 -m pytest -q` completed with 369 passed and the same failure. The failing fixture is `tests/fixtures/multi_ecc_external/plugin.py`: the isolated CRLF checkout does not match its frozen source-byte hash. Gate 03 did not repair or modify that fixture. The timed-out first `make test` attempt and both final transcripts are retained under `baseline/regression/`.
