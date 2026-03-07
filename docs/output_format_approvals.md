# Output Format Change Approvals

This file is the explicit approval ledger for default CLI output format changes.

Policy:
- Any change to tracked default output fixtures under `tests/fixtures/golden/` requires a matching approval entry.
- Each approved change must include one line in the exact format:
  `APPROVED-OUTPUT-FORMAT-CHANGE: <repo-relative-path>`

Approved changes:
- APPROVED-OUTPUT-FORMAT-CHANGE: tests/fixtures/golden/energy_default.stdout.txt
- APPROVED-OUTPUT-FORMAT-CHANGE: tests/fixtures/golden/carbon_default.stdout.txt
- APPROVED-OUTPUT-FORMAT-CHANGE: tests/fixtures/golden/hazucha_default.stdout.txt
- APPROVED-OUTPUT-FORMAT-CHANGE: tests/fixtures/golden/esii_default.json
- APPROVED-OUTPUT-FORMAT-CHANGE: tests/fixtures/golden/smoke_test.stdout.txt
