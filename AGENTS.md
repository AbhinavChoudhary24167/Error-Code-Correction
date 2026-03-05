# Agent Guidelines (Codex)

## Core invariants
- Backward compatibility is mandatory.
- No behavior/schema changes without new explicit flags.
- Prefer additive changes over refactors.

## Commands you must run before finishing
- make
- make test
- python3 -m pytest -q

## Output schema stability
- Do not rename JSON/CSV fields.
- Do not change default CLI output formatting.

## Where to add new ML code
- Put all ML code under ml/
- Keep existing selector as baseline; ML is advisory-only.

## Testing policy
- Add golden tests for existing CLI outputs.
- Add ML tests: deterministic training, OOD fallback, train→predict smoke.
