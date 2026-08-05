# GREEN-ECC DATE 2027 experiment contract

**Contract state:** frozen at Gate 01 on 2026-08-04  
**Repository identity:** branch `main`, commit `f2908466bfa1a8eee8ad5c13b15e0d02a4730351`  
**Intended venue:** DATE 2027 regular research paper, primary topic T3 and secondary topic D9

This contract precedes new correctness work and experimental result generation. Deviations require a dated amendment made before observing the affected results; the original choice, reason, and impact must remain visible.

## Research question and hypotheses

**Primary question.** How much reliability, energy, latency, or area is lost when an SRAM designer selects only a mathematical ECC code while ignoring its RTL implementation, physical bit mapping/interleaving, deployment architecture, scrub policy, workload, and fault environment?

- **H1 — Restricted-selection regret:** Under a preregistered mathematical-code-to-canonical-implementation mapping, mathematical-only selection produces measurable feasibility disagreement, Pareto-set disagreement or normalized objective regret relative to full cross-layer exhaustive DSE. Report the entire distribution, effect sizes and confidence intervals—not merely whether one counterexample exists.
- **H2 — Implementation dependence:** Under identical physical characterization conditions, implementations of the same mathematical code exhibit distinguishable PPA outcomes and may occupy different Pareto regions. Null results must also be reported.
- **H3 — Cross-layer interaction:** Mapping, interleaving, scrubbing, workload and fault locality produce interaction effects on residual SDC/DUE or selected design beyond their isolated main effects. The interaction metric and statistical method must be fixed before experiments.
- **H4 — Carbon non-redundancy:** Candidate-dependent embodied carbon or time/location-dependent carbon intensity changes at least one ranking or Pareto-membership decision relative to energy-only selection. Otherwise, carbon must be declared redundant and removed as an optimization objective.

These are falsifiable claims. H1 is not the tautology that a superset has a weakly better optimum: its endpoints concern a fixed, preregistered restricted procedure and the empirical distribution of disagreement/regret. Failure to cross the practical-effect threshold, indistinguishable PPA, absent interactions, or unchanged carbon decisions is a reportable null result.

## Frozen analysis choices

### Canonical mathematical-only baseline

Map each audited mathematical code to exactly one implementation by registry identity, never by observed performance. Conventional extended Hamming uses `secded-rtl-combinational-72-64-v1`. A code with one registered implementation uses that implementation. For a code with several implementations, any additional mapping must be frozen by stable identifier before characterization. A rejected or unsupported canonical implementation remains infeasible; it is never silently replaced. Gate 02 must freeze the final machine-readable mapping and its SHA-256 before experimental outputs exist.

The restricted selector may choose a mathematical code and then uses only its canonical implementation, fixed reference architecture, reference mapping/interleaving, and reference scrub policy. The full selector enumerates every eligible cross-layer tuple. Both selectors use identical feasibility tests, evidence gates, objective definitions, scenario data, and tie-breaking.

### Endpoints and statistics

- **Primary endpoint:** normalized total-system-energy regret among scenarios where both restricted and full selectors are feasible.
- **Regret equation:** `r_s = (E_restricted,s - E_full,s) / E_restricted,s`.
- Restricted-infeasible/full-feasible cases are a separate feasibility-disagreement endpoint; no artificial infinite regret is assigned.
- **Secondary endpoints:** feasibility-disagreement rate, Pareto-set Jaccard disagreement, physical area regret, latency regret, residual-SDC/DUE differences, and ranking changes.
- **Confidence intervals:** paired BCa bootstrap with 10,000 resamples and seed `1723` for scenario/PPA effect summaries. Empirical fault proportions use exact Clopper–Pearson 95% simultaneous intervals with Bonferroni correction. Exact exhaustive quantities receive no sampling interval.
- **Physical-design seeds:** five common paired seeds for every comparable candidate: `1723`, `2718`, `31415`, `57721`, and `65537`.
- **Cross-layer interaction metric:** preregistered difference-in-differences contrasts on residual SDC/DUE and normalized objective values, supplemented by interaction terms in a factorial model. Multiple interaction tests use Benjamini–Hochberg false-discovery-rate control at 5%.
- **Practical effect criterion:** an effect is called practically meaningful only when it exceeds both the combined 95% uncertainty bound and a sourced system tolerance. If no defensible tolerance exists, report the effect without calling it practically significant.
- Report sample/cell counts, exclusions, missingness, all effect estimates, full distributions, confidence intervals, multiplicity treatment, random seeds, and null results. Do not substitute only a best case or one counterexample.

## Design space

The candidate is the tuple:

`(mathematical code, concrete encoder/decoder implementation, deployment architecture, physical bit-to-cell mapping, interleaving, scrub policy, PVT corner, workload, fault environment)`.

Independent variables are the tuple components, physical-design seed, and time/location carbon trace. Controlled variables are useful payload capacity, technology/library, PVT within a comparison cell, timing constraint, activity/workload trace, memory organization, fault arrivals, design-flow versions, constraint files, and physical-design seeds. Dependent variables are feasibility, residual SDC, DUE, total-system energy, latency, physical area, operational carbon, embodied carbon, Pareto membership, selected tuple, and the preregistered disagreement/regret endpoints.

Every dimension must be represented by an explicit finite registry or configuration file before result generation. The current 15-code/17-implementation/17-architecture/192-scenario repository is an input inventory, not the contracted physical design space: mapping, interleaving, architecture feasibility, physical characterization, and transition accounting are still incomplete.

## Scenario rules and reliability constraints

- **Inclusion:** every preregistered schema-valid Cartesian cell with required evidence and a fair comparison context.
- **Exclusion:** only invalid configuration, failed correctness gate, missing required evidence, or violated fairness identity. Record every exclusion with a code and never remove a scenario after observing its result.
- Freeze the SDC/DUE constraints, system exposure/time conversion, fault-arrival model, physical mapping and adjacency definition before trials. The present `service` and `stringent` thresholds may be retained only if externally justified; otherwise they remain `ASSUMED` sensitivity thresholds and cannot support an absolute reliability claim.
- SDC and DUE must remain separate. Decoder output, undetected/miscorrected output, detected-uncorrectable output, scrub accumulation, and system/FIT conversion must be traceable stages.
- Empirical fault trials require the fixed random seed list in their configuration and a stopping/sample-size rule fixed before outcomes. Exhaustive universes must state exactly which error masks and payload-independence argument are covered.

## Fairness controls

Each comparison requires equal useful payload capacity and identical technology/library, PVT, timing target, activity/workload, memory organization, fault context, and physical-design seeds. Account for the complete codec, parity storage, SRAM macro width/capacity, padding, interleaver, metadata, MUX, controller, scrub traffic, state transition, migration/re-encoding, and routing contribution. Use paired runs for implementation comparisons.

Candidates with different `(n,k)` are normalized by equal useful information capacity, including padding and the integer number of codewords. A comparison that cannot maintain this identity is excluded, not normalized by an ad hoc score. Pipeline cycle latency and combinational delay are separate. Codec-only energy is never labelled total-system energy.

## Carbon contract

Operational carbon is `sum_t(E_candidate,t * CI_location,t / 3.6e6)` with energy in joules and carbon intensity in kgCO2e/kWh. Carbon intensity must vary independently by time/location and candidate workload timing to be a potentially independent objective. A single within-scenario scalar makes operational carbon a monotone rescaling of energy and must not be optimized as a separate objective.

Embodied carbon requires sourced manufacturing intensities, allocation to ECC logic and additional memory area, yield, lifetime, amortization, and end-of-life assumptions with uncertainty. If candidate-dependent embodied carbon is absent and operational intensity cannot change decisions, H4 is null and carbon is removed from the optimization vector.

## Baselines

1. Mathematical-only restricted selector with the frozen canonical mapping.
2. Full exhaustive cross-layer enumeration (reference method).
3. Fixed conventional SECDED using `secded-rtl-combinational-72-64-v1` under the same architecture/mapping/scrub reference.
4. Best single fixed tuple selected without access to held-out scenario outcomes; its training/selection partition must be frozen.
5. Current legacy score-based selector only as a diagnostic if every alias maps one-to-one to a verified implementation; otherwise `NOT ASSESSABLE`.

NSGA-II is not a contracted baseline while exact enumeration is feasible. It may be introduced only after a recorded design-space size makes exhaustive enumeration infeasible, with population, initialization, mutation, crossover, termination, constraint handling, seeds, and exact-enumeration validation on tractable subspaces frozen first.

## Evidence needed for planned claims

| Planned claim | Minimum evidence |
|---|---|
| H1 restricted-selection regret | Gate-02-passing implementations; frozen mapping; complete exhaustive tuple manifest; paired scenario records; exact feasibility/Pareto audit; BCa intervals and full regret distribution |
| H2 implementation dependence | At least two implementations of the same code; identical RTL-to-physical flow and five paired seeds; timing-clean runs; area/timing/activity-power outputs; uncertainty and null reporting |
| H3 cross-layer interaction | Executable mapping/interleaving/scrub/workload/fault factors; calibrated or clearly conditional fault input; frozen factorial cells; difference-in-differences and interaction-model outputs |
| H4 carbon non-redundancy | Time/location trace or candidate-dependent embodied carbon; complete energy/carbon provenance; at least one reproducible ranking/Pareto change, otherwise a declared null and objective removal |
| Absolute FIT/reliability | Calibrated raw fault/flux/Qcrit evidence, physical mapping, temporal model, scrub accumulation, uncertainty, and system exposure conversion |
| Physical PPA or total energy | Identified library/PDK/corner/constraints/tool versions, SRAM macro, placed-and-routed or otherwise justified flow, activity source, full-system accounting, raw reports, and five paired seeds |
| Runtime adaptation | Implemented compatible codeword transition, metadata/state machine, migration/re-encoding, measured/synthesized overhead, failure semantics, and reproducible transition tests |

## Forbidden interpretations

- Do not call generic cell/XOR counts physical area, delay, power, or joules.
- Do not call an analytical sensitivity input measured, calibrated, realistic, or technology-independent.
- Do not generalize an enumerated mask universe beyond its stated error weights and coordinates.
- Do not infer BCH capability from a filename, dimensions, or comment.
- Do not promote the rejected SEC-DAEC/cyclic implementations or the failed TAEC adjacent-triple claim.
- Do not call the current 192-cell analytical grid a physical design-space exploration.
- Do not report `27% energy`, `19% carbon`, `189 scenarios`, universal selector agreement, or an adaptive break-even unless the complete ledger chain is restored.
- Do not treat a larger design space's weakly better optimum as the scientific result.
- Do not claim runtime selection from an architecture manifest or software decision rule.

## Gate order and go/no-go

Gate 01 may inspect existing correctness evidence and run bounded existing verification commands. It must not generate new minimum-distance proofs, repair decoders, redesign codes, expand correctness universes, or present new exhaustive correctness results. Those activities belong exclusively to Gate 02.

Proceed from Gate 01 to **Gate 02: mathematical correctness and exhaustive miscorrection validation** only with this contract and the Gate-01 evidence map frozen. Gate 02 must resolve checkout-stable content identity, then validate matrices/polynomials, encoder/decoder equivalence, stated correction/detection universes, and miscorrection domains for every candidate. No PPA or paper-claim experiment may begin until its candidates pass Gate 02.

Publication experiment go requires: Gate 02 pass; complete fair tuple registry; identified physical flow and SRAM evidence; runnable traceable scripts; frozen seeds/configurations; no unresolved primary endpoint input; and a dry-run provenance chain. No-go is triggered by any missing primary-evidence link, unfair candidate identity, uncalibrated absolute reliability claim, absent implementation-dependent physical data for H2, or carbon remaining a monotone duplicate for H4.
