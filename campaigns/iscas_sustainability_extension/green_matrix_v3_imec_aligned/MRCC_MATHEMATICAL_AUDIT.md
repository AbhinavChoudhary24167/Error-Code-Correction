# MRCC mathematical audit

## Verdict

MRCC is mathematically defined only for a fixed matched baseline and positive
additional correct service.  It is scientifically useful as a transparent
incremental diagnostic after feasibility, but should not be the sole optimum or
be compared across unmatched baselines.  Current U0/E0 data do not qualify it.

## Audit

- Dimensions are carbon divided by service improvement.
- Adding unrelated candidates does not change a fixed pair, so MRCC is
  candidate-set independent.  Changing the baseline changes the estimand and
  must be visible in the metric label.
- `Delta N_correct = 0` is undefined; the implementation returns a reason and
  never divides by epsilon.
- `Delta N_correct < 0` is classified as no incremental reliability gain.  A
  negative denominator is not hidden by a sign convention.
- `Delta C < 0` with `Delta N > 0` produces a valid negative value and signals
  joint carbon/service dominance.
- `Delta C = 0` with `Delta N > 0` gives zero marginal carbon cost.
- If carbon or service is missing for either side, the matched comparison is
  blocked rather than imputed.
- Uncertainty in a small positive denominator can create a heavy-tailed ratio.
  If the denominator distribution crosses zero, report undefined probability
  and the joint `(Delta C, Delta N)` distribution instead of a misleading mean.
- Scaling both candidates to the same request count preserves MRCC only when
  embodied-carbon amortization and lifetime are scaled consistently.
- Payload changes require a payload-bit marginal denominator; access MRCC and
  bit MRCC can rank designs differently.

Alternatives answer different questions.  Incremental carbon per avoided SDC
isolates silent corruptions; per avoided unrecovered service failure combines
SDC, DUE, and SLA failure according to a declared policy; per additional
reliable payload bit handles differing widths.  None should collapse SDC and
DUE when their service consequences differ.  GREEN Matrix 3.0 therefore keeps
the reliability vector and exact Pareto front beside MRCC.
