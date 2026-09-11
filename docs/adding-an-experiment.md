# Adding an experiment

Create a new, uniquely named directory under `campaigns/`. Never overwrite or silently resume a frozen campaign as though it were new.

## Contract before execution

Record:

- research question, hypothesis, claim boundary, success/failure criteria;
- architecture/implementation IDs and useful-payload functional unit;
- tool, image, PDK, library, macro, PVT, constraints, and source commits;
- workload/operation definitions, fault population, seeds, and sampling plan;
- one campaign-wide resource budget and timeout semantics;
- expected raw logs, reports, normalized records, hashes, and validation command;
- how failed/partial runs will be retained.

## Execution and packaging

Write only inside the new campaign/output root. Persist the original start/deadline so resume cannot grant a fresh budget. Capture commands and exit statuses. Normalize results without deleting source reports. Distinguish tool completion, timing, DRC, LVS, signoff, activity coverage, and evidence qualification.

Provide a README, machine-readable status, run manifest, schemas where needed, hashes, validation script, and final report. A validator should be read-only by default and return nonzero for structural or provenance failure.

## Promotion

Promote a quantity only when its producer, boundary, units, dependencies, and qualification rule pass. A partial output can be valuable negative evidence but must retain null/blocked fields. Compare against a parent campaign only with an explicit compatibility map.

Before committing:

```bash
python PATH/TO/CAMPAIGN/validate_package.py
make artifact-check
python -m pytest -q
```
