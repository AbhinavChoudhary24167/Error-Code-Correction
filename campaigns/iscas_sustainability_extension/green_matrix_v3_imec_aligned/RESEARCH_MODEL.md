# Research model

## Three layers that must not be conflated

**Model structure** is a causal equation, such as
`Scope2 = fab_electricity × manufacturing_grid_CI`.

**Parameter value** is the number and unit used in that equation, such as a
specific `kgCO2e/kWh` under a named scenario.

**Evidence status** says whether that number is absent, parametric, published,
derived, tool-estimated, cross-validated, or measured, and whether its boundary
fits the intended claim.

Equation tests validate the first layer only.  Qualification rules join all
three layers for a particular analysis.

## Reliability model

Logical enumeration establishes `P(outcome | injected topology)` only.  A
physical result requires an independently calibrated distribution `P(f)` and
uses `P(outcome) = sum_f P(outcome | f) P(f)`.  Enumeration frequency is never
used as an event probability.

Service outcomes are mutually exclusive: normal correct response, corrected
correct response, correct response after retry, unrecovered detected failure,
silent corruption, timeout/SLA failure, and scrub work.  SDC never earns correct
service credit.  DUE earns none unless an explicit external recovery completes
correctly inside the declared policy and boundary.

## Decision sequence

1. Select a declared physical fault environment, workload, policy, technology,
   implementation, interleaving, fab/grid scenario, lifetime, and boundary.
2. Apply external hard SDC, DUE, latency, and throughput constraints.
3. Reject candidates lacking the required evidence for that analysis.
4. Enumerate exact Pareto fronts for tractable candidate sets.
5. Use CSCI/CSCI_bit for qualified climate-intensity comparisons and MRCC only
   as a fixed-baseline marginal diagnostic.
6. Report uncertainty, boundary, evidence class, and every rejection.

NSGA-II is not used.  It may return only for genuinely large mixed
combinatorial/continuous spaces, and must then reproduce exact fronts on
tractable subsets.

## Partial qualification

Qualification is local to a metric.  Missing SKY130 carbon blocks CSCI and the
sustainability frontier, but does not erase an E4 area observation or an E3
logical control.  Conversely, logical controls never qualify physical SDC/DUE.
The current exact partial frontier is explicitly
`LOGICAL_CONTROL_AREA_DIAGNOSTIC`; it is not selection-eligible.

## Uncertainty

The kernel supports declared intervals, deterministic scenario ensembles, and
seeded Latin-hypercube samples.  Future modules may add defensible Monte Carlo,
bootstrap, and implementation-seed models.  Epistemic uncertainty is distinct
from aleatory variability; scenario envelopes are not confidence intervals.
If a denominator interval reaches zero, an intensity ratio is unbounded or
undefined rather than artificially regularized.
