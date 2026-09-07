# Legacy formula audit

## Verdict

Neither legacy GREEN Score is suitable as the campaign's primary sustainability metric. The historical harmonic score's claimed weakest-component bound is false; the current geometric replacement has the same false bound if claimed, arbitrary anchors/weights, an epsilon leak at zero, and candidate-set dependence when used through the selector. ESII-v2 is bounded and locally monotone but double-counts energy through both energy utility and operational carbon. NESII is explicitly cohort-dependent. EPC remains useful only as a conditional energy diagnostic.

## Harmonic bound

For normalized positive weights summing to one,

\[
H_w=(\sum_i w_i/S_i)^{-1}.
\]

If `m=min_i S_i`, then `S_i>=m`, hence `1/S_i<=1/m`, so `sum(w_i/S_i)<=1/m` and therefore **`H_w>=m`**, not `H_w<=m`. Equality holds only in special cases (for example, all positively weighted components equal `m`). The historical claimed upper bound by the minimum reverses the inequality.

Numerically, for `S=(0.1,1,1)` and `w=(0.6,0.3,0.1)`, `H=1/6.4=0.15625`; the score is 15.625 while `100*min(S)=10`. With `S_r=0`, the epsilon floor produces a small positive score rather than zero.

The weighted geometric mean also lies between the minimum and maximum. For the same scores and weights it is `0.1^0.6=0.2511886`, again above the minimum.

## Property results

| Property | ESII-v1 | ESII-v2 | NESII | GS harmonic | GS geometric/current selector |
|---|---|---|---|---|---|
| bounded | no | yes `[0,1]` | usually `[0,100]`; epsilon makes p95 slightly below 100 | yes under non-negative inputs | yes |
| monotone in declared raw inputs | carbon singularity at threshold | nondecreasing reliability, nonincreasing energy/carbon | monotone within fixed cohort | yes in fixed positive utilities | yes in fixed utilities; selector preprocessing changes mapping |
| dimensional consistency | ratio has FIT/kgCO2e units | utilities dimensionless after fixed anchors | dimensionless cohort points | dimensionless after unit-bearing anchors | dimensionless after unit-bearing anchors |
| candidate-set independence | yes | yes | **no** | standalone yes | standalone yes; **selector no** |
| anchor independence | no carbon threshold | **no** | **no** | **no** | **no** |
| arbitrary-weight independence | n/a | **no** (0.5/0.5 burden blend) | n/a | **no** | **no** |
| sensible zero behavior | **fails** at carbon below epsilon | reliability-neutral candidates always zero | degenerate cohort forced to 50 | epsilon leak | epsilon leak; missing carbon can be rewarded |
| Pareto compatibility | incomplete objectives | non-strict after clamps | cohort mapping only | weakly monotone for fixed mappings | weakly monotone for fixed mappings; cohort preprocessing breaks independence |

## Scale and anchor dependence

ESII-v2 and both GS versions depend on numerical half-saturation constants: 1 kgCO2e, 1 kWh, 10 ns, 0.25 overhead, 0.05 relative FIT gain, or 2 FIT decades. A consistent change of units requires changing each anchor too; the APIs do not carry unit types. Changing kilograms to grams without changing the carbon anchor changes scores and can change rankings when other dimensions trade off.

NESII's p05/p95 or min/max anchors are a function of the evaluated cohort. Adding an unrelated candidate changes existing values. The selector additionally applies cohort-dependent carbon clipping before GREEN Score. `LEGACY_FORMULA_COUNTEREXAMPLES.json` records executable numeric cases.

## Weight dependence and rank reversal

Scalar weights encode preferences that have no physical calibration. Candidate A with `(Sr,Sc,Sl)=(0.2,1,1)` and B with `(0.8,0.4,0.4)` ranks B above A under reliability-heavy `(0.6,0.3,0.1)` but A above B under carbon-heavy `(0.1,0.8,0.1)`. The score cannot prevent an unacceptable SDC rate from being compensated by carbon unless reliability is separately constrained.

## Near-zero and missing-data behavior

- ESII-v1 maps positive improvement with carbon below `10^-12 kg` to zero, a discontinuity opposite to service-per-carbon intensity semantics.
- GS floors zero sub-utilities, so a failed component does not force an exact zero.
- current GS removes the carbon dimension when carbon is unavailable and renormalizes the remaining weights. Missing evidence can therefore improve rather than disqualify a score.
- NESII forces all candidates to 50 for a degenerate small cohort, erasing real provenance differences and creating an arbitrary neutral value.

## Pareto and dominance assessment

For a fixed set of strictly increasing utility transforms and fixed positive weights, harmonic and geometric aggregation preserve strict componentwise utility dominance. That narrow theorem does not rescue the deployed selector because (1) utility transformations saturate/clamp, (2) the selector changes carbon/latency inputs based on the cohort, (3) area, energy, carbon, reliability and latency are causally dependent, and (4) feasibility thresholds are absent. Exact Pareto analysis on physical quantities is retained as the defensible comparison method.

## Retained uses

- ESII-v1/v2, NESII, and both GS generations: legacy ranking comparison and rank-reversal diagnostics only.
- EPC: component/event energy diagnostic when the correction count and energy boundary are explicit.
- raw sub-utilities: sensitivity visualization only, never evidence substitution.
