# Revision-2 experiment and analysis report

Evidence source: fresh Revision-2 runs only. Seeds: 11, 13, 17, 19, 23. Valid routes: 20/20. Final DRC clean: True.

## Seed-sensitivity table

| Architecture | Seeds | Area mean [min--max] um2 | Slack-derived frequency mean [min--max] MHz | Detailed wire mean [min--max] um | Achievable energy mean [min--max] pJ/op | 10 ns feasible |
|---|---:|---:|---:|---:|---:|---:|
| SECDED combinational | 5 | 18649.6 [18594.1--18728.0] | 238.89 [225.65--245.06] | 44917.0 [44609.0--45257.0] | 145.77 [144.83--146.49] | 5/5 |
| SECDED pipelined | 5 | 25587.5 [25486.9--25639.6] | 349.98 [347.54--355.85] | 49964.2 [49703.0--50101.0] | 111.63 [110.76--112.22] | 5/5 |
| Hsiao algorithmic | 5 | 19190.6 [19135.9--19257.2] | 212.91 [207.02--215.62] | 49810.4 [49599.0--50142.0] | 149.57 [148.87--150.77] | 5/5 |
| BCH (78,64,t=2) syndrome/Chien | 5 | 57239.7 [56992.2--57762.9] | 66.64 [65.90--67.66] | 185035.2 [179964.0--191875.0] | unavailable | 0/5 |

## SECDED paired effects

The percentage definition is `(pipelined - combinational) / combinational * 100`. Five values form a deterministic seed-sensitivity envelope; no p-values or population inference are used.

| Effect | Values by seed | Mean | Median | Sample SD | Min | Max | Range |
|---|---|---:|---:|---:|---:|---:|---:|
| Area | 11: 36.70%, 13: 37.27%, 17: 36.84%, 19: 37.44%, 23: 37.76% | 37.20% | 37.27% | 0.43% | 36.70% | 37.76% | 1.05% |
| Detailed wirelength | 11: 12.07%, 13: 10.63%, 17: 10.76%, 19: 11.45%, 23: 11.28% | 11.24% | 11.28% | 0.58% | 10.63% | 12.07% | 1.43% |
| Cell count | 11: 28.25%, 13: 28.23%, 17: 28.06%, 19: 28.30%, 23: 28.45% | 28.26% | 28.25% | 0.14% | 28.06% | 28.45% | 0.39% |
| Slack-derived frequency | 11: 45.91%, 13: 55.34%, 17: 44.99%, 19: 42.12%, 23: 44.78% | 46.63% | 44.99% | 5.07% | 42.12% | 55.34% | 13.23% |
| Total power | 11: -24.02%, 13: -23.80%, 17: -23.53%, 19: -23.24%, 23: -22.52% | -23.42% | -23.53% | 0.58% | -24.02% | -22.52% | 1.50% |
| Achievable energy/op | 11: -24.02%, 13: -23.80%, 17: -23.53%, 19: -23.24%, 23: -22.52% | -23.42% | -23.53% | 0.58% | -24.02% | -22.52% | 1.50% |

## Robustness and dominance

- Pipeline area greater: 5/5.
- Pipeline slack-derived frequency greater: 5/5.
- Pipeline detailed wirelength greater: 5/5.
- Pipeline achievable energy lower: 5/5.
- SECDED target feasibility: combinational 5/5; pipelined 5/5.
- Per-seed SECDED non-dominance: 5/5.
- Aggregate-mean relation: `NON_DOMINATED`.
- Range-sensitive relation: `NON_DOMINATED`.

Scientific interpretation: all four physical/energy orderings persist across every matched seed. Neither SECDED implementation dominates the other at any evaluated seed.

## Hsiao verdict and physical result

`HSIAO_EXACT_IDENTITY_PASS`

The exact miter covered every arbitrary 72-bit received word. The new decoder uses explicit logic comparison rather than the historical inferred 256x73 table, and its RTL was frozen before PPA. Hsiao 10 ns feasibility is 5/5. Its physical measurements belong to the new algorithmic hardware identity; only behavior/code semantics transfer by proof.

## BCH result

The evaluated, unchanged syndrome/Chien BCH realization has 10 ns feasibility 0/5. This is an implementation-scoped result, not a statement about BCH as a family. Target-clock energy is excluded for every timing-infeasible seed.

## Correct timing terminology

The reported metric is the **post-route slack-derived frequency estimate** of the fixed implementation optimized at 10 ns: `1000 / (10.0 - signed_worst_setup_slack_ns)` MHz. The signed setup slack is retained; separately displayed WNS is clipped at zero only by convention. No frequency sweep or re-optimization at the derived period was performed.
