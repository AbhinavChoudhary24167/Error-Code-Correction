# GSE theorem and property audit

Define lifecycle carbon over a declared, non-overlapping boundary as

\[
C_{LC}=C_{emb}+C_{op}+C_{replacement},
\]

where local scrub/retry/recovery energy appears once inside `C_op`. For `S>=0` and `C_LC>0`:

\[
GSE={S\over C_{LC}}\ [correct\ useful\ payload\ bits/kgCO2e],\qquad
GCI={C_{LC}\over S}\ [kgCO2e/correct\ useful\ payload\ bit]
\]

with GCI defined only for `S>0`.

## Proven properties

**P1 dimensional consistency.** Numerator and denominator retain physical units. Bits-to-bytes divides numeric GSE by eight; kg-to-g multiplies the denominator by 1000 and divides numeric GSE by 1000. Ordering is invariant under a common positive unit conversion.

**P2 positive-domain well-definedness.** Ordinary division is finite on `S>=0,C>0`; `GSE(0,C)=0`. Zero/negative/non-finite carbon is rejected rather than hidden by epsilon. GCI rejects zero service.

**P3 service monotonicity.** `partial GSE/partial S=1/C>0`.

**P4 carbon monotonicity.** `partial GSE/partial C=-S/C^2<=0`, strict for `S>0`.

**P5 dominance consistency.** If `S_A>=S_B` and `C_A<=C_B` with one strict inequality and the positive-domain conditions hold, then `S_A/C_A>S_B/C_B`. The result follows by multiplying the two non-negative improvements; the zero-service boundary is strict whenever service improves from zero or carbon strictly falls for positive service.

**P6 candidate-set independence.** GSE has only the candidate's `S` and `C` as arguments. No cohort statistic appears.

**P7 unit-scaling consistency.** For positive constants `a,b`, `GSE(aS,bC)=(a/b)GSE(S,C)`. Common conversions cannot reverse order.

**P8 baseline-relative interpretability.** `GSE_R=GSE_c/GSE_U0`; because the denominator is positive, `GSE_R>1` iff candidate service per carbon exceeds U0. For matched `B,N`, `GSE_R=(Q_c/Q_U0)(C_U0/C_c)`.

**P9/P10 no arbitrary weights or cohort anchors.** The definition has neither weights nor percentiles/medians. Reliability feasibility is not numerically compensated inside the scalar.

**P11 asymptotes.** At fixed carbon, GSE grows linearly with service and tends to infinity as service does. At fixed finite service, GSE tends to zero as carbon tends to infinity. At zero service it is zero for every positive carbon. `C->0+` is an explicit unbounded limit, not epsilon-clipped.

**P12 uncertainty compatibility.** Pointwise GSE remains valid for every positive-carbon sample. Mean, median, p05/p95, and interval bounds are reported without assuming that a ratio of means equals a mean of ratios. Risk-policy selection remains a separate declared decision.

**P13 Pareto compatibility.** Every `(S,C)` dominator has strictly larger GSE by P5. GSE may order non-dominating tradeoffs; exact Pareto membership is therefore reported before scalar ranking.

All properties have deterministic randomized/exhaustive checks in `tests/test_green_metric_properties.py`.

## Limitations that are not metric failures

GSE cannot decide whether an SDC rate is acceptable, define a missing lifecycle boundary, or convert unqualified measurements into evidence. If no externally defensible reliability/timing threshold exists, selection remains Pareto over `GCI, SDC, DUE, latency`. A high-GSE but unacceptable-SDC design is infeasible only under a declared constraint; otherwise it is reported, not silently selected.

## Retention decision

GSE/GCI are retained as the primary functional-unit metrics. They pass the required mathematical suite. Their scientific qualification is conditional on qualified service and lifecycle-carbon inputs; this theorem does not qualify any current ECC winner.
