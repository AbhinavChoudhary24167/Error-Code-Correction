# Portfolio co-synthesis stage reviews

Review date: 2026-08-03. All numerical PMFs below are deterministic synthetic
benchmarks. Structural costs are not physical PPA.

## Stage 1 - novelty and exact feasibility: pass for prototype

The literature gate retains only the narrow conjunction documented in
`PORTFOLIO_COSYNTHESIS_NOVELTY_GATE.md`; it does not establish a publication
novelty claim. The `(8,4)` exact run examined all 7,920 allowed systematic
matrices and proved the configured optimum. Across 16 data words and 18 modeled
errors (288 executed decoder cases), the generated code corrected probability
`0.91`, produced DUE `0.09`, SDC `0`, and residual `90 FIT` from a `1000 FIT`
raw rate. Equal-redundancy SECDED corrected `0.48` with SDC `0`.

Decision: proceed to a falsifiable single-code prototype. This demonstrates
feasibility only; the selected matrix is closely related to a column-remapped
SECDED construction and is not presented as a new algebraic code family.

## Stage 2 - single-code synthesis: conditional pass

The deterministic `(72,64)` beam search produced a verifier-certified feasible
code, without an optimality claim. It corrected `0.983915078095` of the modeled
spatial-hotspot PMF, with DUE `0.016084921905`, SDC `0`, and residual
`16.084921905 FIT`; equal-redundancy SECDED corrected `0.35`.

The small exact ablations attribute the reliability gain to PMF weighting:
weighted synthesis corrected `0.91`, while a uniform-synthesis matrix evaluated
on the target PMF corrected `0.67`. Hardware-aware and reliability-only searches
selected the same small matrix and cost, so no hardware-aware benefit is shown
there. Relaxing the SDC constraint raised corrected mass to `0.97` but introduced
SDC `0.03`; the hard SDC limit prevented that trade.

Decision: proceed to portfolio experiments, retaining the scalable-search and
synthetic-PMF limitations.

## Stage 3 - portfolio and shared hardware: negative hardware result

For two `(72,64)` modes, alternating search reduced weighted residual probability
from the independently specialized start `0.475244385880` to `0.400766164329`.
One general generated code gave `0.510528217256`. The accepted trajectory used
shared-XOR proxies `350 -> 358 -> 366 -> 369`.

The final joint point therefore improved reliability but used **more** shared XOR
proxy gates than independent hardware-aware generation followed by the same CSE
pass (`369` versus `350`). Other structural baselines were 820 naive per-equation
XOR gates, 594 for separately optimized engines plus 16 MUX proxy units, and
1,072 for the programmable-fabric proxy. Yosys/ABC was unavailable, so the
mandatory ordinary-synthesis baseline and all physical area/energy/leakage/delay
claims remain unsupported. SEC-DAEC, TAEC, and BCH are recorded as incompatible
where no dimension-matched, matrix-certified repository artifact exists; they are
not assigned invented numbers.

Decision: retain the open implementation and negative result; do not claim a
shared-hardware PPA improvement.

## Stage 4 - shift safety: negative robustness result

Both specialized modes satisfy SDC `0` on their design PMFs, but several shifted
PMFs cause substantial SDC (roughly `0.26-0.33` on broad/voltage-sensitive cases).
SECDED is safe for the SBU/DBU-only design regimes, but is not automatically safe
for triple-bit and mixed-MBU shifts. The policy falls back only when the fallback
certificate passes and otherwise rejects deployment.

Decision: specialization is not robust without an envelope monitor and certified
fallback. The improvement does not survive arbitrary distribution shift.

## Stage 5 - end-to-end deployment: blocked by missing physical inputs

The generated mode IDs and required characterization are exported in
`scheduler_integration.json`. Scheduler execution is deliberately blocked because
no characterized per-access energy, leakage, critical path, configuration,
migration, re-encoding, or synthesis-tool comparison is available.

Decision: no claim that the portfolio remains beneficial after transition costs.
This is an evidence boundary, not a software failure.

