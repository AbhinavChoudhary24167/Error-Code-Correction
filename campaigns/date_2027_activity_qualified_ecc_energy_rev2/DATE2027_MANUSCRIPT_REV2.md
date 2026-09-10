# When ECC Energy Ordering Depends on Activity: A Matched Post-Route Study

Anonymous submission

## Abstract

Dynamic-power reports are conditional on the activity used to stimulate a realized circuit. We ask whether an error-correcting-code (ECC) energy ordering survives replacement of vectorless post-route estimation by operation-specific activity while the routed implementation and extracted parasitics remain fixed. Conventional Hamming-style and Hsiao single-error-correcting, double-error-detecting (SECDED) logic are routed at five matched deterministic seeds and a 10-ns target; all ten runs meet timing. Final-gate-netlist activity covers idle, clean write, clean read, single-bit correction, and double-bit detection at the routed-ECC-logic boundary. Vectorless analysis favors Hsiao in 5/5 seeds, but operation-specific energy favors it in only 4/23 matched operation/seed comparisons. Mean Hsiao-minus-conventional deltas are -0.0308 pJ/clean read, +0.1207 pJ/write, +0.3095 pJ/correction, and +0.1935 pJ/detection. Internal and net-switching components oppose one another in several read modes. Compact exact-equivalence and feasibility controls show why hardware structure, implementation condition, and target admission were frozen before substituting activity. The result is not an architecture ranking: under the evaluated conditions, the ordering depends on the stated activity and measurement boundary.

Keywords: ECC, SECDED, Hsiao code, post-route power, switching activity, matched physical design.

## I. Introduction

ECC semantics determine correction and detection behavior, but not a unique circuit or physical energy. RTL organization fixes register placement and transaction timing; synthesis and place-and-route determine cells, wiring, and parasitics; an activity model determines which capacitances and cell states are exercised. Moving a conclusion across any of these boundaries can change the quantity being claimed.

This matters for memory ECC because the logic sees structured events. Writes, clean reads, corrections, detections, and idle windows sensitize different cones. Transition-density and power-estimation studies established that signal statistics condition dynamic-power estimates [1], [2]. Ghosh, Basu, and Touba went further for memory ECC: they optimized Hamming and Hsiao check matrices using SPEC and MediaBench traces [3]. Their work rules out any broad claim that trace-aware ECC power analysis or Hamming/Hsiao activity sensitivity is new.

Our narrower question is whether a winner obtained from vectorless post-route power remains the winner after operation-specific activity is applied to the same physical states. That question requires more than functional labels. Earlier qualified experiments in this repository showed that exact-equivalent temporal SECDED implementations can move substantially in area, timing, latency, and energy, whereas an exact-equivalent flat/hierarchical Hsiao transformation produces a smaller mixed displacement. Re-implementing the temporal pair at a second target changes effect magnitude. These observations motivate the controls used here: a test of activity identity must freeze hardware identity, implementation condition, routed state, feasibility status, and parasitic association.

We compare conventional Hamming-style and minimum-odd-weight-column Hsiao SECDED logic [4] under one 10-ns SKY130HD flow and seeds {11, 13, 17, 19, 23}. Each final routed netlist is timing-qualified. Vectorless power and final-gate-netlist VCD power then use that run's own final SPEF. The measured quantity is operation-normalized ECC-logic energy; SRAM-macro-internal energy is excluded.

The contributions are: (1) an evidence-qualified method that separates semantic, formal/functional, hardware, physical, timing, parasitic, and activity identities before admitting an energy comparison; (2) a paired post-route dataset of ten timing-feasible implementations, 46 qualified activity records, and 23 matched operation/seed comparisons, in which the Hsiao-lower vectorless ordering held in 5/5 seeds but survived in only 4/23 operation-specific comparisons; and (3) a controlled interpretation that connects the activity result to exact-equivalent temporal and structural transformations, condition sensitivity, component accounting, and a stronger-correction feasibility boundary without turning those controls into independent headline claims. The primary DATE identity is D9 through activity-conditioned energy; D13 is secondary through post-route matching and evidence association.

## II. Related Work

Hsiao codes minimize odd-weight parity-check columns for SECDED [4]; later work targets delay or adjacent-error guarantees [5], [6]. Stronger-correction and memory studies explore latency, redundancy, density, and adaptive protection [7]--[11]. These works show why code construction and system context matter, but they do not make an implementation's energy independent of its activity source.

Ghosh et al. is the closest verified comparator [3]: it uses application memory traces and directly studies Hamming and Hsiao checker power. Our distinction is experimental rather than conceptual. We preserve each final routed architecture/seed state and its extracted parasitics, replace only the activity abstraction, normalize by completed operations, and test whether the induced ordering changes across matched seeds. In the literature set audited for this paper, we found no study of that complete matched final-route ordering-substitution question; this is an awareness claim, not proof of universal absence.

OpenROAD and OpenLANE support inspectable RTL-to-layout studies [12], [13], while equivalence methods support qualification of transformations [14], [15]. Flow repeatability alone, however, does not prevent a timing report, VCD, and SPEF from referring to different physical states. Their association is therefore part of the claim.

## III. Evidence-Qualified Methodology

### A. Qualification boundaries

The evidence chain is: ECC semantics; correctness qualification; hardware identity; temporal or structural state; routed physical identity; timing feasibility; final parasitics; activity identity; and operation-normalized energy. Temporal structure, implementation condition, and activity are distinct experimental dimensions. Controls establish the first two; the main experiment freezes them and substitutes the third. Figure 1 is regenerated as `figures/revised_final/figure01_evidence_pipeline.*`.

Exact-equivalence claims are pair-specific. For conventional SECDED, zero-plus-basis affine encoder qualification and compositional decoder qualification establish identical systematic (72,64) transaction behavior after shifting pipelined responses by two cycles. Request latency is one versus three cycles and the initiation interval remains one; encoder and decoder response/status fields are aligned. For flat versus hierarchical Hsiao, arbitrary-word SAT proves decoder equality and temporal induction proves same-cycle equality at the registered transaction boundary; both have one-cycle latency and II=1. Conventional SECDED versus Hsiao has distinct internal codeword representations. We qualify their common interface and W1-correction/W2-detection contract and do not claim exact codeword equivalence.

### B. Physical and activity identity

All main-study runs use SKY130HD at the nominal typical corner, the same interface, 64-bit payload, physical-flow policy, constraints, and 10-ns target. Seeds 11, 13, 17, 19, and 23 are paired within architecture comparisons. They are deterministic perturbations of physical-design heuristics, not Monte Carlo process samples, fabricated-chip samples, or independent draws from a physical population.

Each measurement uses the exact final zero-delay routed gate netlist associated with its timing result and that run's final SPEF. Hash joins bind architecture, seed, routed netlist, SPEF, VCD/workload, and power result. The vectorless diagnostic uses the flow's default activity assumptions. The operation-specific estimator uses idle, clean write, clean read, correctable single-bit read, and detectable double-bit read. Sixteen warm-up cycles precede 256 measured operations. For architecture *a*, seed *s*, and operation *o*,

`E[a,s,o] = P[a,s,o] T[s,o] / N[o]`, with `N[o] = 256`.

The paired effect is `Delta E = E[Hsiao] - E[conventional]`; a negative value favors Hsiao. Power and energy magnitudes are not compared across estimators; only their matched architecture orderings are compared.

Every admitted record represents all 72 SRAM-output activity roots. Functional logic coverage is 99.298390--99.356061%, including 100% sequential and approximately 99.2% combinational coverage. Coverage qualifies annotation completeness, not workload representativeness. Seed 11 lacks qualified idle and write counterparts, so those classes have four pairs; no value is imputed. Means, sample standard deviations, ranges, and sign counts are descriptive. The matched physical pair is the statistical unit; no population-significance claim is made.

The measurement boundary is routed ECC logic around the memory interface. The open SRAM characterization lacks the macro-internal switching energy required for a whole-memory result. The numbers are therefore post-route ECC-logic estimates, not chip or silicon measurements.

### C. Compact reproducibility contract

A record is admitted only after route completion, nonnegative setup WNS at 10 ns, final-netlist and final-SPEF association, VCD parsing, representation of all 72 output roots, coverage calculation, and successful component/energy extraction. The artifact retains hashes, commands, generated data, scripts, all figures, and the two unavailable seed-11 pairs. A failed identity join makes a result unavailable rather than zero.

## IV. Experimental Design and Controls

The paper distinguishes Q1, hardware identity: can qualified RTL restructuring change physical outcome? Q2, implementation condition: can a target change modify effect magnitude? Q3, activity identity: can activity substitution change architecture ordering when routed state is fixed? Q3 is the principal experiment; Q1 and Q2 justify its controls.

| Study | Change | Held fixed / qualification | Condition; pairs | Main observed effect | Role |
|---|---|---|---|---|---|
| Temporal SECDED | combinational to pipelined | Same systematic transaction relation; exact two-cycle response alignment; II=1 | 10 ns; 5 | Area +37.201864%, timing +46.629355%, energy/op -23.419005%; directions 5/5; latency 1 to 3 | Hardware-identity control |
| Temporal SECDED | same RTL pair, tighter target | Same qualification and pair identities | 5 ns; 5 | Area +36.721138%, timing +68.629653%, energy/op -19.336606%; directions 5/5 | Condition control, not activity replication |
| Structural Hsiao | flat to hierarchical decode | Same matrix, interface, latency=1, II=1; exact arbitrary-word and boundary proofs | 10 ns; 5 | Area -0.564122%, wire +3.867152%, vias +3.918161%, timing +2.655651%, energy +1.328395% | Small mixed structural control |
| BCH feasibility | stronger W1/W2-correcting realization | Named syndrome/Chien RTL; common physical target | 10 ns; 5 | Evaluated realization timing-feasible in 0/5 attempts | Categorical admission boundary |
| Main activity study | conventional SECDED versus Hsiao | Interface/reliability contract, 10-ns flow, matched routes | 10 ns; 5 | Vectorless favors Hsiao 5/5; operation-specific energy favors it 4/23 | Principal experiment |

The temporal control changes state placement, request latency, clock burden, and switching behavior together; it shows why hardware identity cannot be transferred. The structural Hsiao control shows that a distinct implementation need not move by much. The 5-ns result belongs only to the temporal SECDED pair and is not a 5-ns replication of conventional-versus-Hsiao operation energy. BCH has a different correction guarantee and is excluded from the 23 activity comparisons. The evaluated BCH(78,64,t=2) syndrome/Chien realization did not meet the common 10-ns target in the five matched implementation attempts. This is a categorical result for that realization, not a statement about BCH as a family.

## V. Results

### A. Physical qualification and ordering substitution

All ten main-study implementations route and meet the 10-ns setup target. Across matched seeds, Hsiao-minus-conventional mean changes are +237.6 um2 total instance area, +237.2 um2 standard-cell area, +2992.8 um wire, +467.8 vias, and +0.2437 ns setup WNS. Hsiao has higher WNS in four of five pairs. Both architectures are admitted before energy is compared.

The headline ordering matrix is `figures/revised_final/figure02_activity_ordering.*`. Vectorless post-route power favors Hsiao in all five matched seeds. Operation-specific energy favors it in only 4/23 cells: 3/5 clean reads and 1/4 idle windows, with no Hsiao-lower write, correction, or detection pair. Both estimators refer to the same qualified routes and parasitics, so the mismatch is an activity-model ordering change rather than a different-implementation comparison.

| Operation | n | Mean Hsiao-minus-conventional delta (pJ/op) | Hsiao lower |
|---|---:|---:|---:|
| Idle | 4 | +0.019108014 | 1/4 |
| Clean write | 4 | +0.120681918 | 0/4 |
| Clean read | 5 | -0.030837887 | 3/5 |
| Correction | 5 | +0.309499691 | 0/5 |
| Detection | 5 | +0.193505204 | 0/5 |

### B. Operation-specific energy

Figure 3 (`figures/revised_final/figure03_operation_energy_deltas.*`) exposes all 23 paired values. Clean read is the sole operation with a negative mean, but its seed range is -0.213 to +0.171 pJ/op. A single route could therefore support either read ordering. Correction has the largest mean displacement and favors conventional SECDED in 5/5 pairs.

For an illustrative active mix whose nonnegative weights sum to one,

`Delta E = 0.1207 w_write - 0.0308 w_read + 0.3095 w_corr + 0.1935 w_det`.

For read/write traffic alone, the arithmetic-mean model crosses zero at a 79.6476% clean-read fraction. This is an engineering interpolation of operation means, not a workload-trace result or a selector study.

### C. Component accounting

Figure 4 (`figures/revised_final/figure04_component_decomposition.*`) separates internal, net-switching, and dynamic power; dynamic is internal plus switching, while leakage remains in the source table. For clean reads, Hsiao has lower net-switching power in 5/5 seeds (mean -28.973363806 uW) and higher internal power in 5/5 (mean +25.890767574 uW). The mean dynamic difference is -3.082596232 uW, leakage is +0.000082946 uW, and total energy is -0.030837887 pJ/op.

Correction has mean internal, switching, dynamic, leakage, and total-energy differences of +35.456381738 uW, -4.518486094 uW, +30.937895644 uW, +0.000057446 uW, and +0.309499691 pJ/op. Detection gives +30.415412039 uW, -11.072447524 uW, +19.342964515 uW, +0.000050363 uW, and +0.193505204 pJ/op. Internal is higher in 5/5 correction and detection pairs; switching is lower in 3/5 and 4/5, respectively. These reports are consistent with internal and switching contributions competing after mapping and operation sensitization. They do not prove which net-level mechanism caused the totals.

### D. What the controls establish

At 10 ns, pipelined-minus-combinational SECDED changes standard-cell area by +37.201864%, the signed-slack-derived timing metric by +46.629355%, and equal-work steady-stream energy/op by -23.419005%; directions hold in 5/5 pairs while latency changes from one to three cycles. Fresh 5-ns routes preserve the directions but change the mean timing and energy effects to +68.629653% and -19.336606%. This answers Q1 and Q2 only.

Hierarchical-minus-flat Hsiao produces a smaller mixed displacement: area -0.564122%, detailed wire +3.867152%, vias +3.918161%, timing +2.655651%, and energy +1.328395%. Exact semantic and temporal identity does not eliminate physical displacement, but it does not prescribe a large effect. Implementation identity determines what must be measured separately; it does not predict the magnitude or sign of the resulting displacement.

## VI. Discussion, Threats, and Conclusion

Q1 shows why a behaviorally qualified architecture change cannot borrow another implementation's PPA. Q2 shows why the implementation target belongs to physical identity. Those controls justify freezing both before Q3. Once frozen, replacing vectorless assumptions with operation-specific activity changes the observed Hsiao-lower ordering from 5/5 physical pairs to 4/23 operation/seed cells. The controls are deliberately insufficient as stand-alone contributions here: deleting them would leave the headline result understandable but weaken its experimental justification.

The 4/23 count describes the complete matched table. Its cells share hardware identities and operation definitions and are not 23 independent samples from a physical population. The count is not a probability or an application-independent loss rate. Similarly, the vectorless result is not labeled inaccurate; it answers a different question under the flow's default activity assumption.

The component table shows that net switching can decrease while internal power increases enough to change dynamic and total signs. It does not identify whether the internal term arose from a particular cell state, transition slew, path sensitization, or glitch sequence. The read/write crossover omits temporal correlation, burst boundaries, idle residency, error rate, macro activation, and application traces.

Fairness is defined at the declared boundary. Conventional and Hsiao SECDED satisfy the same external interface and correction/detection contract, use the same flow and target, and are paired by physical seed; their parity organization and internal codeword representations intentionally differ. Exact codeword identity is not claimed. The BCH point is also narrow: alternative BCH architectures, parallelism, pipelining, field arithmetic, constraints, or libraries could change feasibility.

Threats include controlled operations rather than application traces; zero-delay final-routed-gate-netlist activity, which omits some delay-induced glitches; missing SRAM-macro-internal energy; five deterministic matched seeds rather than a probabilistic physical population; missing seed-11 idle/write pairs; one vectorless baseline configuration; one principal library/corner/width and 10-ns activity-aware condition; pair-specific formal boundaries; a 5-ns result limited to the temporal SECDED control; and a BCH result limited to one syndrome/Chien realization.

The central result would be falsified by a mismatched VCD/SPEF/route identity, a timing-infeasible admitted implementation, a regenerated sign change, or a 23-cell table that does not contain four negative deltas. A different ordering under another technology, route policy, activity source, or workload would define a new physical or activity identity and test generality rather than invalidate this conditional record.

Under the evaluated conditions, a vectorless architecture ordering does not generally survive operation-specific activity. Component accounting shows that lower net switching can coexist with higher internal power and higher total operation energy. The controls establish why temporal structure, implementation condition, and feasibility must be fixed before interpreting that substitution. An ECC energy claim should identify the implementation, physical condition, activity source, operation normalization, and measurement boundary together.

## References

The canonical, audited bibliography is `references.bib`. It contains the 15 works numbered [1]--[15] in the compiled manuscript; metadata and authoritative identifiers are recorded in `DATE2027_REFERENCE_AUDIT.csv`.
