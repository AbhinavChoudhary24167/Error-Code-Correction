# Legacy versus GSE

No numerical U0/E0 ranking comparison is scientifically admissible. The legacy
metrics need reliability, energy/carbon, latency, corrections, or cohort anchors
that are not jointly qualified; GSE/GCI likewise need physical useful-service
probability and lifecycle carbon. Empty cells in `LEGACY_VS_GSE.csv` mean
unavailable, not zero or a tie.

The formula-level comparison is nevertheless decisive:

- GSE/GCI are candidate-set independent and respect strict service/carbon
  dominance on their positive domain.
- NESII and the deployed selector are cohort-dependent; adding a candidate can
  change existing values.
- the historical harmonic weakest-component upper-bound proof reverses its
  inequality (`H_w >= min(S_i)`, generally not `<=`);
- legacy weights and anchors can reverse rankings, and missing carbon can be
  rewarded after selector weight renormalization;
- legacy GREEN Score may remain only a compatibility diagnostic, not a primary
  selection rule.

The executable counterexamples are in `LEGACY_FORMULA_COUNTEREXAMPLES.json`.
Actual architecture disagreement remains `NOT_EVALUATED`, not assumed.
