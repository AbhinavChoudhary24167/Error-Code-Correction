# GREEN Matrix v3.2 final scientific report

Schema version: `3.2.0`

Campaign commit: `UNCOMMITTED_VALIDATION_BUILD`

Parent campaign commit: `1f6bcd009e7a05ebcde35a3272161a9a81ec7bf7`

Foundation commit: `affc8145b184803189dac36391cb486f00e7b4f8`

Generation date: `2026-09-08`

## Outcome

GREEN Matrix v3.2 implements an additive **Evidence -> Qualification ->
Conditional Model -> Decision** framework. It preserves the frozen v3.1
physical population, makes `M_E`, `M_P`, and `M_S` first-class artifacts,
populates exact conditional logical-response surfaces, and performs exact
diagnostic and conditional-scenario Pareto enumeration. Absolute physical
reliability and lifecycle conclusions remain blocked.

Final classification:
`GREEN_MATRIX_V3_2_EVIDENCE_AWARE_DECISION_MODEL_CONDITIONAL_FRONT_VALIDATED_ABSOLUTE_RELIABILITY_AND_LIFECYCLE_BLOCKED`.

The sustainability method is methodologically informed by publicly available
imec SSTS/imec.netzero bottom-up principles. No certification, compliance,
validation, standardization, or endorsement by imec is claimed, and no public
imec datum is represented as SKY130 manufacturing data.

## Required questions

1. **What changed from GREEN 3.1 to 3.2?** Evidence is now an executable operand of every decision: each quantity carries tier, boundary, uncertainty/status, provenance, compatibility, allowed uses, forbidden uses, and dependencies. Exact conditional response, admissibility, scenario robustness, and three distinct Pareto objects were added.
2. **Which new quantities became populated?** Five-seed E4 diagnostic means/intervals for six implementation metrics per architecture; E3 conditional corrected, detected, SDC, and DUE probabilities for four logical mask classes per U0/E0; and conditional scenario-space non-dominance fractions.
3. **Did any quantity reach E5?** No. `E5_MEASUREMENT_COUNT = 0`.
4. **What exact criterion defines E5 activity completeness?** All ten requirements in `data/ENERGY_QUALIFICATION.json` must pass: complete annotation, zero unmatched/unannotated objects, no default activity, post-route gate/glitch activity, macro-internal characterization, whole-service coverage, isolated positive operation window/count, declared clock, and complete provenance hashes.
5. **Were read/write/correct/retry/scrub energies separately established?** No; all remain `BLOCKED`. Only the inherited seed-11 partial-annotation total is retained as E4 diagnostic energy per requested service.
6. **Were I1/I2 physically implemented?** No. I0 remains the routed baseline; I1/I2 remain proposals.
7. **What physical overhead did they incur?** No I1/I2 overhead is reported: area, wirelength, vias, power, energy, latency, II, slack, and congestion are unavailable rather than imputed.
8. **Is any physical reliability benefit attributable to interleaving?** No; neither a routed nontrivial interleaver nor a complete physical/logical mapping exists.
9. **Was bitcell/logical mapping improved?** No. Macro geometry and partial electrical organization remain available; address-to-column group, bitcell identity, bitcell XY, and physical-to-logical ECC-bit identity remain blocked.
10. **Was Qcrit established?** No. `QCRIT = BLOCKED`.
11. **Was any physical event-rate model established?** No. Logical injection/enumeration frequencies are explicitly forbidden as event-rate substitutes.
12. **Can physical SDC now be calculated?** No; the event occurrence and mapping operands are missing.
13. **Can physical DUE now be calculated?** No; the same absolute-probability guard blocks it.
14. **Can FIT now be calculated?** No; no qualified physical event rate exists.
15. **Were conditional SDC/DUE response surfaces established?** Yes, for U0/E0 over logical SBU-any-bit, DBU-any-pair, consecutive-MBU-3, and consecutive-MBU-4 classes, using exact inherited logical enumeration.
16. **What exactly is conditional vs absolute reliability?** Conditional results are `P(outcome | declared logical mask class, architecture)`. Absolute rates require `P(T_i)` or an event rate plus a verified physical-to-logical topology map; those operands remain unavailable.
17. **Was any literature quantity transferred into SKY130?** No. The five v3.1 literature records remain native, technology/process/geometry-mismatched references. `LITERATURE_NUMERIC_TRANSFER_TO_SKY130 = FORBIDDEN`.
18. **Was manufacturing carbon established?** No. `SKY130_MANUFACTURING_CARBON = BLOCKED`.
19. **Were external manufacturing scenarios added?** No; the reference-manufacturing-scenario count is zero.
20. **What claims may those scenarios support?** None were added. A future mismatched reference scenario could support declared sensitivity analysis only, never an absolute SKY130 carbon claim.
21. **Can CSCI be populated?** No. The equation/guard may be audited, but lifecycle carbon and absolute correct-service operands are blocked.
22. **Can MRCC be populated?** No. Its equation/guard remains separable from unavailable matched lifecycle/reliability operands.
23. **Does a qualified Pareto front exist?** No: `QUALIFIED_FRONT_BLOCKED`.
24. **Does a diagnostic Pareto front exist?** Yes: `DIAGNOSTIC_FRONT`, over route area, wirelength, and vectorless tool power.
25. **Does a conditional scenario front exist?** Yes: five exact `CONDITIONAL_SCENARIO_FRONT` objects.
26. **Which dimensions were used?** Conditional SDC probability, five-seed mean routed area, and five-seed mean vectorless power; the diagnostic front uses area, wirelength, and vectorless power. No normalization was applied and all directions are minimization.
27. **What scenario assumptions were required?** Five explicit logical-topology mixtures: four pure mask classes and one equal mixture. They are researcher-declared assumptions, not physical PMFs or evidence.
28. **What is each architecture's scenario-space non-dominance fraction?** U0 = `1.0` and E0 = `1.0` under finite uniform counting over the five declared scenarios.
29. **Is that fraction a physical probability?** No. It is not yield, confidence, silicon optimality, or probability of winning.
30. **Is a global architecture winner qualified?** No: `NO_GLOBAL_WINNER_QUALIFIED`.
31. **What remains structurally blocked?** Physical event rate/PMF, complete bitcell mapping, Qcrit, absolute SDC/DUE/FIT, E5 and operation-separated energy, saturated throughput, routed I1/I2 overhead, SKY130 manufacturing/lifecycle carbon, CSCI, MRCC, and a qualified sustainability front.
32. **What is now the highest-value accessible next experiment?** An activity-complete, operation-isolated post-route campaign that satisfies `E5_ACTIVITY_COMPLETE_V3_2`, followed by matched routed I1/I2 experiments.
33. **What is the highest-value ultimate reliability experiment?** `MATCHED_SKY130_SRAM_PARTICLE_BEAM_EVENT_COORDINATES_FLUENCE_AND_VERIFIED_BITCELL_LOGICAL_MAP`.
34. **What claims are appropriate for ISCAS?** The evidence-aware cross-layer method; exact conditional logical-response surfaces; explicit boundary/compatibility guards; a reproducible five-seed diagnostic implementation demonstration; and exact conditional trade-space analysis with visible blockers.
35. **What claims remain forbidden?** Silicon or radiation validation, Qcrit, physical SKY130 SDC/DUE/SER/FIT, E5 energy, saturated throughput, routed interleaver benefit, absolute manufacturing/lifecycle carbon, CSCI/MRCC values, a qualified sustainability front, imec endorsement, or a global winner.

## Scientific interpretation

The established causal order is physical event topology -> logical corruption
-> ECC/interleaving response -> service outcome -> operational resource
consequence -> lifecycle consequence. `M_E` gates every transition. Missing
evidence stops downstream absolute claims, while exact conditional analysis is
retained inside its declared logical abstraction boundary.
