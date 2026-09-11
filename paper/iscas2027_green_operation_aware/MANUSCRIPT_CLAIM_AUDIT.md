# Manuscript claim audit

Audit date: 2026-09-09. Evidence seal: `8cf245ac6ac8cb9b010c073d439f04eb204d48a1`.

## Paragraph-level audit

The paragraph identifiers below follow the rendered manuscript order. “Ledger” refers to `GREEN_CLAIM_LEDGER.md`; numbers and provenance are independently reproduced in the generated JSON/CSV artifacts.

| Paragraph | Technical purpose | Principal support | Scope or rewrite decision | Result |
|---|---|---|---|---|
| Abstract | State question, matched design, headline counts, operation deltas, and boundary. | C01, C03, C06–C09, C22, C26 | Calls values estimates and explicitly excludes macro/whole-memory and silicon. | PASS |
| I-1 | Motivate why activity identity can alter an energy comparison and pose the question. | Najm [1]; Ghosh et al. [2] | Does not claim vectorless estimation is incorrect. | PASS |
| I-2 | Bound the gap against ECC, workload, physical-flow, and cross-layer prior art. | Hsiao [3]; [2], [4]–[10]; `RELATED_WORK_AUDIT.md` | Uses “focused audit did not identify”; makes no first/unique claim. | PASS |
| I-3 | State three retained contributions. | C01, C14–C19 | “Contributions” are method/result/formulation, not a new code or tool. | PASS |
| II-1 | Define GREEN evidence vector and missing-data rule. | C19, C21–C23 | Missing quantities are neither zero nor substituted. | PASS |
| II-2 | Apply reliability/timing admission before preference. | C16–C17 | BCH statement is limited to the evaluated implementation; U0 is excluded by the declared requirement. | PASS |
| II-3 | Define operation mixture, preference sign, scenario policy, and carbon extension. | C14–C15, C20–C21 | Probabilities and CI remain declared parameters; absolute lifecycle carbon blocked. | PASS |
| II-4 | Define the only qualified architecture-mean Pareto front. | C18–C19 | Front uses qualified means; variability is reported elsewhere. | PASS |
| III-1 | Identify designs, functional evidence, PVT, seeds, timing, and tool provenance. | C02, C16; Ajayi et al. [11] | Reliability remains coding/RTL, not a physical soft-error rate. | PASS |
| III-2 | Define operation classes, warm-up, sample count, activity source, SPEF, and coverage. | C03–C05 | Activity is simulated zero-delay final-routed activity; coverage definition is explicit. | PASS |
| III-3 | Give E5 record counts, seed-11 exclusions, reported components, and energy boundary. | C03, C22 | Macro-internal and whole-memory energy explicitly blocked. | PASS |
| III-4 | State matched descriptive statistical policy. | C06–C13 | Bootstrap/leave-one-out are sensitivities; no significance or population claim. | PASS |
| IV-A1 | Quantify area/routing/timing tradeoff. | C11–C12 | Avoids “better PPA” and universal timing superiority. | PASS |
| IV-A2 | Quantify E4 vectorless diagnostic. | C13 | Does not relabel E4 as operation energy. | PASS |
| IV-B1 | Compare E4 and E5 with distinct denominators and interpret only ordering stability. | C01 | Explicitly says vectorless analysis is not intrinsically wrong. | PASS |
| IV-C1 | Report every requested operation mean and seed consistency. | C06–C09 | Clean-read exceptions and n=4 write denominator remain visible. | PASS |
| IV-C2 | Interpret internal/switching/leakage decomposition. | C10 | Uses “consistent with”; rejects causal mechanism C24. | PASS |
| IV-C3 | Interpret leave-one-out and bootstrap sensitivities. | C06–C09 | No probability-population or statistical-significance language. | PASS |
| IV-D1 | Give complete-case five-operation workload coefficients. | C14 | Uses the four jointly complete seeds, not mixed-denominator means. | PASS |
| IV-D2 | Derive general Hsiao-lower inequality. | C14 | Pure algebra from the qualified complete-case coefficient vector. | PASS |
| IV-D3 | State the two-dimensional slice and all-available-means sensitivity. | C15 | Fixed assumptions are visible; boundary precision warning retained. | PASS |
| IV-D4 | Interpret qualified fronts and reject a global winner. | C18–C19 | Distinguishes area-energy and area-timing-energy objective sets. | PASS |
| V-1 | Restate the narrow finding and physical tradeoff. | C01, C06–C13 | Remains five-seed, 10 ns, ECC-logic scoped. | PASS |
| V-2 | Enumerate threats and their consequences. | C17, C20–C23, C26–C27 | No blocked or rejected claim is presented positively. | PASS |

## Sentence-level controls

- All numerical manuscript claims trace to `GREEN_PAIRED_STATISTICS.json`, `GREEN_WORKLOAD_ANALYSIS.json`, `GREEN_PARETO_RESULTS.json`, or `GREEN_REPRODUCIBILITY_TABLE.csv`.
- The manuscript contains no “first,” “unique,” “optimal,” “state-of-the-art,” “statistically significant,” foundry-signoff, imec-endorsement, or silicon-validation claim.
- “Power” is used for E4/component quantities; “energy” is used for operation-normalized E5 quantities.
- E4 and E5 denominators are stated separately and never treated as exchangeable samples.
- Observed component signs are separated from an untested gate-level causal explanation.
- Every positive conclusion maps to a ledger status of `SUPPORTED`, `SUPPORTED_WITH_SCOPE`, `MODEL_DEPENDENT`, or `ANALYTICAL_ONLY`.
- C21–C26 appear only as exclusions, limitations, or rejected generalizations.

## Remaining production work

The scientific draft passes the claim audit. Camera-ready typesetting, author metadata, final ISCAS template conformance, and the conference’s final page-limit check remain submission-production tasks, not evidence gaps.
