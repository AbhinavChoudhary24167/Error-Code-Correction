# Novelty Red-Team

## Strongest attack

“Power depends on activity; Najm established this decades ago, and Ghosh et al. already used real traces for ECC checker power. The result is obvious and not novel.”

## Response

The general dependence is known and explicitly credited. The non-obvious result is that an architecture ordering observed unanimously under the flow's vectorless estimator fails in 19/23 matched operation/seed cells after activity substitution, despite preserving physical feasibility, routed-netlist identity, and final parasitics. The paper contributes a controlled falsification of a common inference, not the proposition that activity matters.

## Other attacks and required restraint

1. **“The comparison is just another Hamming-versus-Hsiao benchmark.”** The manuscript must foreground ordering invariance, not crown a code.
2. **“Five seeds are too few.”** Use paired descriptive counts and ranges; prohibit population p-values and universal rankings.
3. **“The macro dominates memory energy.”** Agree; label the boundary ECC logic in abstract, captions, method, threats, and conclusion.
4. **“Zero-delay VCD misses glitches.”** Treat as a named estimator limitation; do not call it silicon power.
5. **“Missing idle/write data invite cherry-picking.”** Show dashes, denominators, and no imputation.
6. **“The vectorless baseline is underspecified.”** Call it the flow's diagnostic baseline, publish the raw component deltas, and do not generalize to every vectorless model.
7. **“Open-source flow use is not novelty.”** Agreed; flow citations provide provenance context only.
8. **“The component explanation is post hoc.”** Present it as diagnostic interpretation, not causal proof.
9. **“The ISCAS manuscript already uses these results.”** Shared evidence is permissible, but the DATE paper must have a different question, title, abstract, contribution list, main figures, and conclusion; the separation audit documents this.

## Red-team verdict

Defensible if the contribution remains: *matched post-route evidence that an ECC architecture ordering is conditional on the activity abstraction*. Not defensible if expanded into a universal Hsiao/Hamming ranking, whole-memory result, first-ever activity-aware ECC claim, or sustainability claim.
