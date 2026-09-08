# GREEN Matrix 3.0 final report

## Outcome

GREEN Matrix 3.0 establishes a normalized, evidence-aware foundation for joint
memory reliability and sustainability research.  It replaces the flat,
all-fields-required v2 research model with independent physical (`M_P`),
evidence (`M_E`), and scenario translation (`M_S`) matrices, metric-specific
qualification, exact Pareto analysis, explicit system boundaries, and a
configuration-driven design-space tensor `G[A,N,F,I,W,P,G,L,M]`.

The initial population contains 14 immutable-v2-derived U0/E0 observation rows,
210 quantity-level evidence records, and two deliberately blocked SKY130
lifecycle translations.  No missing physical rate, energy, latency, lifetime,
yield, or manufacturing-carbon value was fabricated.  Four exact logical-
control/area diagnostic fronts can be enumerated, but none is a physical
reliability or sustainability selection.

The manufacturing evidence status remains
`SKY130_MANUFACTURING_CARBON_NOT_QUALIFIED`.

Final classification:
`GREEN_MATRIX_V3_FOUNDATION_VALIDATED_IMEC_ALIGNED_PARTIAL_POPULATION`.

“IMEC aligned” here means `IMEC_PUBLIC_EVIDENCE_ALIGNED`; it does not mean imec
certified, compliant, endorsed, standardized, or foundry-specific.

## Required questions

1. **Why was GREEN Matrix v2 superseded?** Its monolithic rows coupled unrelated
   qualification, and its GSE/GCI-centered view was too weak for independent
   physical, evidence, and sustainability evolution.  V3 uses linked sparse
   matrices and metric-local gates.
2. **Which previous artifacts remain valid?** All historical GREEN/GSE/GCI,
   Attempt09/10, DATE, calibration, experiment, and regression artifacts remain
   immutable provenance in their original boundaries.  Exact logical controls,
   observed area, diagnostic activity/power, source metadata, yield algebra,
   and ACT algebra remain useful under their original labels.
3. **Which previous metrics remain useful?** ESII, NESII, legacy GREEN Score,
   GSE, and GCI remain executable comparison metrics classified
   `LEGACY_OR_COMPARISON_METRIC`; they are not the v3 selector.
4. **What is the new functional unit?** One correct payload-bearing memory
   service under declared workload, policy, payload, SLA, fault environment,
   and boundary; correct payload-bit service is used across differing widths.
5. **What is Matrix P?** Physical/architectural observations: ECC, SRAM,
   implementation, mapping, workload/policy identity, PVT, PPA/energy/latency,
   and conditional reliability controls—never lifecycle carbon or a GREEN score.
6. **What is Matrix E?** Quantity-level value, unit, source, hashes, technology,
   PVT/workload/boundary, tier, kind, uncertainty, citation, status, and reason.
7. **What is Matrix S?** Recomputable mapping of qualified physical designs into
   fab/grid/lifetime/boundary scenarios with separate Scope 1, Scope 2,
   upstream, mask, package, operation, lifecycle, service, and decision fields.
8. **What is the master design-space representation?** Sparse relations
   implementing `G[A,N,F,I,W,P,G,L,M]`, not a dense array.
9. **Is CSCI mathematically defensible?** Yes, conditionally: `C_LC/(N_req Q)`
   is dimensionally sound, candidate-independent, and monotone on its positive-
   service domain, after hard feasibility and with matched boundary/evidence.
10. **Is payload-normalized CSCI preferable?** For unequal payload widths, yes;
    for an identical fixed access width the access form is simpler.  Rankings
    can differ, so both are reported with the functional unit.
11. **Is MRCC mathematically defensible?** Yes as a fixed-matched-baseline
    marginal diagnostic when `Delta N_correct > 0`; it is not the primary
    selector.
12. **Where is MRCC undefined?** Missing matched inputs or
    `Delta N_correct = 0`.  Negative service improvement is classified as not an
    incremental reliability gain and sent to dominance/Pareto analysis.
13. **Does either metric exhibit candidate-set dependence?** CSCI and fixed-pair
    MRCC do not depend on unrelated candidates.  MRCC depends explicitly on the
    chosen baseline, which is part of its estimand.
14. **Are epsilon floors used?** No.
15. **How are reliability constraints defined?** As external workload/policy-
    dependent bounds on SDC, DUE, latency, and throughput applied before
    sustainability comparison; no universal thresholds are invented.
16. **How are SDC and DUE separated?** They remain distinct outcomes, constraints,
    evidence quantities, and Pareto axes; policy determines external recovery.
17. **How are logical controls distinguished from event probabilities?** Logical
    rows are labelled `ENUMERATED_MASK_FREQUENCY_NOT_EVENT_RATE`.  Physical
    outcomes require independent `P(f)` and total-probability aggregation.
18. **How is interleaving represented?** As a first-class axis and registry with
    coordinate-to-logical/codeword/bank/word/symbol mapping plus independent
    controller/routing/wirelength/energy/latency/distance/reliability costs.
19. **How is scrub policy represented?** In the service-policy registry with
    interval, activity, energy, latency, retry, and service-credit semantics.
20. **How is workload represented?** A registry record for read/write/correction/
    retry/scrub counts, duty cycle, request count, time, and evidence; the seed
    workload currently has identity but missing quantitative parameters.
21. **How is manufacturing carbon modelled?** Bottom-up process route to unique
    steps, equipment electricity, gases, upstream terms, wafer, yield/good die,
    mask/package, then an explicit architecture allocation.
22. **How are Scope 1 and Scope 2 separated?** Scope 1 is released unabated
    process-gas mass times declared GWP; Scope 2 is purchased step electricity
    times manufacturing-grid CI.
23. **What upstream terms are included?** Only individually declared supported
    components.  Current SKY130 upstream data are unavailable; the framework
    does not claim complete Scope 3.
24. **How is process-route complexity represented?** Ordered, unique process
    steps grouped by module, not a node-name scalar.
25. **How are EUV/DUV effects represented?** As complete route differences in
    exposures, deposition, etch, clean, and other modules; scanner wattage alone
    cannot establish the result.
26. **How is yield represented?** Explicit Poisson, negative-binomial, Murphy,
    or measured models with density/units, area, alpha, line yield, and source.
27. **How is good-die carbon calculated?** Wafer carbon divided by
    `N_gross × Y_die × Y_line`, plus only in-boundary, separately declared terms.
28. **How is mask NRE handled?** Separately amortized over production good dies;
    it is never multiplied into every wafer route and remains parametric when
    absolute burden is unknown.
29. **How is ECC embodied carbon allocated?** Prefer matched marginal die-size/
    yield impact; area proportional is diagnostic only.  Current SKY130 status
    uses no allocation because evidence is insufficient.
30. **How is operational carbon calculated?** Disjoint read, write, correction,
    retry, scrub, and idle energy over lifetime, explicitly converted J to kWh,
    times use-grid CI.  Overlapping correction energy is rejected.
31. **How are manufacturing and use grids separated?** Independent scenario IDs
    and carbon intensities in `M_S`.
32. **How is lifetime represented?** A scenario axis holding request/activity
    counts, duration, duty cycle, replacements, and assumptions; it is currently
    undeclared and therefore blocks lifecycle metrics.
33. **What current imec evidence is used?** Public virtual-fab/SSTS methodology,
    PPACE/EDTM history, the 2023 cradle-to-gate study, and lithography evidence,
    always through registered sources and native boundaries.
34. **What imec evidence is trend-only?** PPACE/EDTM advanced-node evolution,
    N28-to-projected-A14 energy/process complexity, and route-level EUV effects
    where full matched numeric inventories are absent.
35. **What is not transferable to SKY130?** All advanced-node imec numeric
    coefficients, yields, grids, gas inventories, and projected-node outputs.
36. **Does the framework reproduce available imec trends?** It reproduces
    linear grid and abatement direction exactly, process-complexity direction as
    `TREND_REPRODUCTION`, route interactions qualitatively, and refuses an
    absolute SKY130 comparison.
37. **How does it cross-check ACT?** A boundary-matched independent synthetic
    vector exactly reproduces ACT's area/yield coefficient equation (0.8125
    kgCO2e); unmatched defaults are rejected.
38. **How does it compare conceptually with ACT3?** ACT3 supplies configurable
    system/BOM modeling; v3 adds memory fault/service semantics, linked evidence
    gating, and process-step extensibility.  Adapters preserve boundaries rather
    than copying defaults.
39. **What evidence tiers exist?** E0 absent, E1 parametric, E2 published/model,
    E3 analytical/RTL/logical, E4 synthesis/PnR estimate, E5 matched activity-
    qualified post-route, E6 independent cross-validation, E7 silicon/fab
    measured; applicability is still metric-specific.
40. **How does partial qualification work?** Every analysis declares required
    quantities, minimum tiers, allowed classes, and parameter permission;
    failures are enumerated without invalidating unrelated evidence.
41. **Which current analyses are qualified?** Framework/unit/formula behavior,
    source/boundary guards, yield/scope algebra, matched ACT algebra, and exact
    logical-control/area diagnostics.
42. **Which current analyses are parametric?** Explicitly supplied grid, gas,
    yield, good-die, lifetime, and uncertainty scenarios.  They never become
    absolute claims through execution alone.
43. **Which current analyses remain blocked?** Physical reliability, qualified
    energy/latency, SKY130 manufacturing/lifecycle carbon, physical interleaving
    benefit, CSCI/MRCC population, and sustainability selection.
44. **Are any architecture winners currently defensible?** No:
    `NO_GLOBAL_WINNER_QUALIFIED`.
45. **What partial Pareto frontiers can already be generated?** Four exact
    U0/E0 area-versus-logical-SDC/DUE diagnostic fronts, one per enumerated mask
    control.  They are `LOGICAL_CONTROL`, not physical-selection evidence.
46. **How is uncertainty represented?** Explicit epistemic/aleatory intervals,
    scenario ensembles, deterministic Latin-hypercube samples, and future
    defensible Monte Carlo/bootstrap/seed distributions; envelopes are not CIs.
47. **What currently dominates uncertainty?** Structural absence of physical
    event probabilities, matched energy/latency, SKY130 inventory/yield, and
    physical interleaver implementation—not sampling error around known values.
48. **How can a new technology node be added?** Add technology, process-route,
    step inventories, fab/grid/yield scenarios, sources, boundaries, and evidence
    records through configuration.
49. **How can a new ECC architecture be added?** Add one architecture-registry
    record and its implementation/reliability observations and evidence.
50. **How can a new fab/manufacturing dataset be added?** Register the source and
    native boundary, add route/step energy/gas/upstream/yield data, and map a fab
    scenario; no CSCI equation change is needed.
51. **How can physical SER/MBU data be added?** Add topology/radius/event rates
    with technology/PVT/geometry provenance and combine them with conditional
    outcome mappings using total probability.
52. **How can a new SRAM compiler be added?** Add compiler/technology/geometry
    identity to new `M_P` observations and quantity-level hashes/evidence to
    `M_E`; old compiler rows remain unchanged.
53. **Can the framework eventually include water/resource impacts?** Yes, as
    separate environmental metrics and translation tables, not folded into CSCI.
54. **What scientific claims are suitable for ISCAS?** The linked evidence-aware
    framework; correct-service functional units; mathematical CSCI/MRCC domain
    analysis; physical/logical separation; bottom-up manufacturing/service
    coupling; partial qualification; and exact diagnostic fronts.
55. **What claims remain unsupported?** Absolute SKY130 carbon, physical
    SDC/DUE/FIT, activity-qualified service energy/latency, interleaving benefit,
    technology-dependent architecture ranking, and any GREEN winner.
56. **What single experiment would increase qualification the most?** A matched,
    technology/PVT/geometry-specific physical SBU/DBU/MBU topology-and-rate
    characterization.  It converts existing conditional logical controls into
    physical SDC/DUE and makes the hard feasibility stage possible.  Matched
    post-route energy/latency and SKY130 manufacturing inventory follow.
57. **Is GREEN Matrix 3.0 scientifically stronger than v2?** Yes as a foundation:
    it removes cohort weighting as the primary decision rule, isolates causal
    and evidence layers, preserves missingness, enforces boundaries/units,
    supports process steps and physical mappings, and explains partial failure.
    This strength does not manufacture a currently unsupported winner.

## ISCAS positioning

A defensible present contribution is an evidence-aware framework jointly
linking physical memory fault topology, ECC/interleaving implementation,
workload/policy energy, bottom-up semiconductor manufacturing, lifetime carbon,
and correct-service-normalized impact without arbitrary composite weights or
candidate-cohort normalization.  The current paper claim must emphasize
methodology, mathematical audit, evidence gaps, and partial diagnostics—not an
ECC or node winner.

## Next evidence

The first priority is calibrated physical fault topology/rate evidence.  It is
followed by matched architecture-level post-route activity, energy, and latency;
a physically implemented interleaver campaign; and a traceable SKY130-native
manufacturing/yield inventory.  Until those arrive, explicit missingness is the
scientifically correct result.
