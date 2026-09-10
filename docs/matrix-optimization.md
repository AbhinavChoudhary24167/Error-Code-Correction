# Matrix and optimization framework

GREEN Matrix v3 represents a sparse design space `G[A,N,F,I,W,P,G,L,M]` over architecture, node/route, fault model, interleaver, workload, policy, grid, lifetime, and metric. It separates evidence (`M_E`), physical/architectural observations (`M_P`), and scenario/lifecycle translations (`M_S`).

## Dimensions and objectives

Possible objectives include SDC, DUE, FIT, area, wirelength, power, operation/service energy, latency, throughput, operational carbon, manufacturing carbon, and lifecycle carbon. Each analysis declares its subset, unit, direction, constraints, and evidence threshold. Sparse missing dimensions stay missing.

## Eligibility and dominance

For minimization objectives, candidate `a` dominates candidate `b` when every objective of `a` is no worse and at least one is strictly better:

```text
for every j: f_j(a) <= f_j(b)
and for at least one j: f_j(a) < f_j(b)
```

Before this test, GREEN applies implementation verification, fairness/context matching, reliability/service constraints, and non-null objective checks. Epsilon dominance is supported but current exact studies may set epsilon to zero. Equal objective points with distinct identities are retained.

## Normalization and scalar scores

The v3 evidence-aware decision flow does not require cohort normalization or one default scalar score. When normalization is used for a plot or legacy metric, its reference set and direction must be recorded. ESII, GREEN Score, NESII, GSE, and GCI are implemented legacy/comparison metrics; their weights, half-saturation values, or cohort bounds are model and policy choices. They are not universal scientific rankings.

## Pareto, knee, and hypervolume

The repository includes exact Pareto enumeration and an independent validator. A geometric two-objective knee is the point farthest from the normalized extreme-point chord; it is an annotation, not the default winner. Two-dimensional hypervolume is calculated against a recorded reference point and is an audit statistic. Neither establishes statistical significance.

## Deterministic selection

The registry study chooses among feasible candidates with an explicit lexicographic rule over modelled energy, structural complexity, encoded bits, and identifier. That rule is a declared decision policy. The campaign matrices instead expose qualified, diagnostic, and conditional fronts; a partial front cannot be promoted to a global winner.

## NSGA-II and uncertainty

Some design-space code supports population-based or portfolio search, but a returned optimizer population is not itself experimental evidence. Fixed seeds make the search reproducible within the implementation. Uncertainty studies use explicit deterministic scale tuples, scenario ensembles, Latin-hypercube samples, or bootstrap procedures as declared by each study. Scenario sensitivity is not automatically a confidence interval.

## Current conclusion

The available evidence does not span all required reliability, whole-memory energy, and lifecycle dimensions. Therefore:

`No globally qualified ECC winner is claimed.`

See [Pareto and selection](PARETO_AND_SELECTION.md) for the generated registry study and [Evidence model](evidence-model.md) for eligibility.
