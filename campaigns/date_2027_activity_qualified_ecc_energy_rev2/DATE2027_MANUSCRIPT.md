# When ECC Energy Ordering Depends on Activity: A Matched Post-Route Study

Anonymous submission

> This is the reader-facing Markdown companion. `DATE2027_MANUSCRIPT.tex` is the authoritative typeset source and contains the full wording, equations, captions, and references used in the PDF.

## Abstract

Hardware comparisons often treat a power report as an intrinsic property of an architecture, even though dynamic power is conditional on the activity model used to stimulate the implementation. We test whether error-correcting-code (ECC) energy ordering survives a change from vectorless estimation to operation-specific switching activity. Conventional and Hsiao SECDED logic are implemented through matched physical flows at five seeds and a 10-ns target. Every run routes and meets setup timing. For activity-based analysis we preserve the exact routed netlist and final parasitics, then annotate final-gate-netlist VCDs for idle, clean write, clean read, single-bit correction, and double-bit detection. The boundary is ECC logic around the memory interface; macro-internal and whole-memory energy are not claimed. Vectorless reports rank Hsiao lower-power in 5/5 seeds. Under operation-specific activity, Hsiao is lower-energy in only 4/23 matched operation/seed cells: 3/5 clean reads, 1/4 idle cases, and none of the write, correction, or detection cases. Mean Hsiao-minus-conventional deltas are −0.0308 pJ/read, +0.1207 pJ/write, +0.3095 pJ/correction, and +0.1935 pJ/detection. Thus, for these implementations, energy ordering is not invariant to the switching-activity abstraction.

## 1. Introduction

Coding theory, RTL, physical design, and activity modeling answer different questions. A low-weight parity-check structure may suggest less switching, and a vectorless report may appear to confirm a lower-power architecture, but neither establishes the energy of an operation on the realized circuit. Clean reads, corrections, detections, writes, and idle intervals sensitize different cones and internal transitions.

This paper compares functionally matched 64-bit conventional and Hsiao SECDED logic under the same interface, memory organization, constraints, open PDK, cell library, flow, target period, and five physical seeds. Each activity record uses its own timing-qualified final routed netlist and final SPEF. The contributions are: an activity-conditional ordering estimand; a fully paired set of ten physical runs, 46 activity records, and 23 operation/seed cells; and evidence that a unanimous vectorless ordering fails under explicit operations.

## 2. Related work and missing comparison

Hsiao introduced minimum odd-weight-column SECDED codes. Later ECC work explores latency, protected-bit choices, stronger correction, adaptive coverage, and memory-system tradeoffs. Najm established the relationship between activity statistics and power. Ghosh, Basu, and Touba are the closest power-specific precedent: they used application traces to reduce memory ECC checker power. Consequently, the paper does not claim that activity-aware ECC analysis is new.

The narrower gap is a matched final-route experiment that holds the routed implementation and extracted parasitics fixed, applies both a diagnostic vectorless estimator and explicit operation activity, and asks whether the conventional-versus-Hsiao ordering changes across the same seeds. OpenROAD/OpenLANE make the flow reproducible, while equivalence work motivates functional assurance; neither supplies this comparison.

## 3. Experimental method

The two designs provide the same memory-facing behavior and SECDED capability. Seeds 11, 13, 17, 19, and 23 are implemented at 10 ns in SKY130 HD at the nominal typical corner. A cell enters the analysis only if route succeeds and setup timing is feasible. The architecture varies across a pair; physical variation is controlled within seed; activity varies while the routed state remains fixed.

The vectorless diagnostic uses the physical flow's default activity assumptions. Operation-specific records annotate measured VCD activity for idle, clean write, clean read, correctable single-bit read, and detectable double-bit read. Sixteen warm-up cycles precede 256 measured operations. Energy is annotated logic power times measured duration divided by completed operations. Delta is always Hsiao minus conventional, so negative favors Hsiao.

Every record covers all 72 SRAM-output activity roots. Functional logic coverage is 99.298390–99.356061%, with 100% sequential coverage. There are five pairs for each read-derived class and four for idle/write because seed 11 lacks qualified records. Values are not imputed. The boundary includes routed ECC logic but excludes SRAM-internal energy, whole-memory energy, and silicon measurement.

## 4. Results

All ten physical runs meet the 10-ns target. Mean Hsiao-minus-conventional deltas are +237.6 µm² total instance area, +237.2 µm² standard-cell area, +2992.8 µm wirelength, +467.8 vias, and +0.2437 ns setup WNS. Hsiao has better WNS in four of five pairs.

Vectorless total logic power favors Hsiao in all five seed pairs. Operation-specific energy favors Hsiao in only 4/23 cells. Clean read has the only negative operation mean (−0.0308 pJ/op) and is Hsiao-lower in 3/5 seeds. Write is +0.1207 pJ/op and Hsiao-lower in 0/4; correction is +0.3095 and 0/5; detection is +0.1935 and 0/5; idle is +0.0191 and 1/4. Clean-read values span −0.213 to +0.171 pJ/op, demonstrating why one seed cannot settle the ranking.

Components clarify, but do not causally prove, the mechanism. On clean read, Hsiao switching power is lower in all five pairs (mean −28.97 µW), while internal power is higher in all five (+25.89 µW). Correction and detection also reduce mean switching but raise internal power by more, making total deltas positive in every pair. Write mean switching rises by +12.18 µW. Leakage is negligible at this scale. A lower parity-switching intuition therefore does not guarantee lower total operation energy after mapping, buffering, routing, and sensitization.

The answer is conditional and direct: for this population, architecture ordering is not invariant to the activity abstraction. The vectorless ranking fails for 19/23 operation cells and for four of five operation means.

## 5. Discussion

An ECC energy result should identify architecture, implementation state, timing qualification, activity source, operation normalization, and measurement boundary. Workloads can be represented as mixtures of measured operation primitives. Ignoring idle, the mean delta for weights on write, clean read, correction, and detection is `0.1207wW − 0.0308wR + 0.3095wC + 0.1935wD` pJ/op. For a clean-read/write-only illustrative mixture, Hsiao has a negative mean only above about 79.7% clean reads. Error-handling events move the mean toward conventional SECDED. This is a transparent scenario calculation, not an application prediction.

The result does not say Hsiao codes are generally inefficient or that vectorless analysis is useless. Different libraries, synthesis, pipelines, periods, and workloads may change the outcome. Vectorless power is an early diagnostic; the error is promoting its ranking into a workload-independent conclusion.

## 6. Threats to validity

The operation classes are controlled micro-workloads, not application traces. The VCD comes from zero-delay simulation and omits delay-induced glitch behavior. Macro-internal energy is unavailable. The seed population is small, and two cells are missing. Only one width, technology/library/corner, target period, toolchain, and two SECDED organizations are evaluated. Hashes prove identity, not semantic correctness. These limits prohibit whole-memory, silicon, application-average, statistical-significance, and universal architecture claims.

## 7. Replication and falsification

A numerical audit should recover 23 paired cells, four negative deltas, the operation means above, and absent seed-11 idle/write cells. An artifact audit should verify netlist/SPEF/VCD/workload hashes, timing admission, warm-up, operation count, root coverage, and result identity. A full-flow replication should record its own versions and treat additional seeds as a new population. Identity mismatches invalidate affected cells rather than merely increasing uncertainty.

## 8. Conclusion

In ten timing-feasible post-route implementations, vectorless reports favored Hsiao SECDED in 5/5 matched seeds, while final-netlist operation activity with final parasitics favored it in only 4/23 cells. Conventional SECDED was lower for every available write, correction, and detection pair. The defensible lesson is not a universal winner: ECC energy ordering is conditional on activity, implementation state, normalization, and boundary.
