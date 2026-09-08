# Attempt10 Pareto analysis

The raw matrix contains 5760 scenario rows. None has the complete, unit-validated energy, lifecycle-carbon, latency, and physical-reliability evidence required by the declared objective set, so the eligible set is empty. The normalized matrix retains explicit ineligibility markers and no scores.

`PARETO_RESULTS.json` therefore reports no frontier, dominated solutions, hypervolume, knee point, or scenario winner. Exact deterministic non-dominated sorting is implemented for a future qualified finite matrix; NSGA-II is unnecessary for an enumerated set and is not run on missing evidence. The repository's deterministic selector remains the baseline and is unchanged.
