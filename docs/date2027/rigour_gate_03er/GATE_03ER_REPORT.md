# Gate 03E-R: Reproducibility Adjudication and Fresh Rerun

Verdict: `ENVIRONMENT_ENABLEMENT_FAILED`

Policy v2 was frozen at `2026-08-14T12:38:01.226182Z`, before runs 3 and 4. Two new, sequential GCD runs used the pinned image and unchanged official make invocation. Semantic physical outputs, technology XML, stage ODBs, mapped masters, and all frozen QoR rules passed. The overall comparison failed because `run-metadata.json` contained the unresolved differing field `run_label` (`gcd-run-03` versus `gcd-run-04`); post-freeze exclusion is prohibited.

The four preserved GREEN-ECC mapping jobs were revalidated by hashes and properties without rerunning them: PASS. Gates 01, 02, 03, and 03R, Gate 03E v1, and old run trees were rehashed: UNCHANGED. Gate 03R remains `REMEDIATION_FAILED`. The required full repository tests also failed only because unchanged legacy Gate 03/03E scope validators reject the new additive Gate 03E-R paths; the focused Gate 03E-R suite passed.

Policy v1, comparator v1, preserved runs 1–2, and their FAIL result were not modified. Raw hashes remain available for audit; execution timings and resource measurements are recorded but not equality-gated.
