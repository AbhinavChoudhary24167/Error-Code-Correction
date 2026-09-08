# Liberty sensitivity analysis

Strict runs executed: **30/30**. Final-artifact completeness: **20/30**.

Only the SRAM macro output-transition model varied in strict runs. Attempt09 remains FAIL / KEEP_GATE3_FAILED; no diagnostic view changes the independent 0.351 ns rstb requirement. Both diagnostic U0 views caused RSZ-0090 at global placement for every seed after removing the artificial output violations. The failure itself is optimizer-behavior evidence; missing U0 PPA is NOT_MEASURED. Separately labeled exploratory attempts showed suppressing the message does not suppress its exception and produced no PPA.

| Model | Design | Runs | route clean | setup/hold clean | external DRV clean |
|---|---|---:|---:|---:|---:|
| ORIGINAL | U0 | 5 | 5 | 5 | 0 |
| ORIGINAL | E0 | 5 | 5 | 5 | 0 |
| CORRECTED | U0 | 0 | 0 | 0 | 0 |
| CORRECTED | E0 | 5 | 5 | 4 | 0 |
| PIN_SPECIFIC_OR_NO_GLOBAL_COUNTERFACTUAL | U0 | 0 | 0 | 0 | 0 |
| PIN_SPECIFIC_OR_NO_GLOBAL_COUNTERFACTUAL | E0 | 5 | 5 | 4 | 0 |

Across five completed E0 pairs, CORRECTED versus ORIGINAL changes mean standard-cell area by -6.752%, wirelength by 0.738%, vias by -7.533%, and tool-estimated total power by -0.508%. CORRECTED and the no-global counterfactual produce identical E0 metrics, but only four of five corrected runs remain setup/hold clean and every seed retains non-output slew violations. U0 is even more sensitive: both diagnostic views abort at RSZ-0090 in all five strict seeds because no buffering solution meets 0.351 ns after the artificial output violations are removed.

All ten ORIGINAL design/seed runs reproduce Attempt09 selected metrics and deterministic ODB/DEF/SDC hashes exactly. GDS and SPEF byte hashes differ only in regenerated date-bearing formats and are recorded separately. PPA materiality uses the predeclared 1% rule. Power remains a comparative post-route tool estimate. Energy/access remains NOT_QUALIFIED. These results are not a foundry correction or signoff waiver.
