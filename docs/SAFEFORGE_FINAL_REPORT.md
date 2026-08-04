# GREEN-ECC SafeForge final phase report

All probabilities below are conditional on the explicitly declared finite error universe. All small-study comparisons carry experiment ID `4a60649076810a34d09d`. The nominal PMF, expanded support, ambiguity configuration, physical ordering, dimensions, outcome semantics, normalization, and units are identical across the five strategies.

The motivating retained failure is the earlier spatial-hotspot portfolio mode evaluated on the synthetic voltage-sensitive PMF: SDC `0.3342857143` (`334.2857` SDC FIT at raw FIT 1000). SafeForge does not compare that number directly with the small study; it treats it as evidence that nominal specialization needs an explicit envelope.

## 1. Are the existing matrices genuinely new?

No existing Forge matrix is claimed as a new ECC family. The exact `(8,4)` matrix is provably extended-Hamming/Hsiao-equivalent to the baseline under a data-column permutation. The distance-four 72-bit portfolio matrices are odd-column SECDED/Hsiao constructions. The distance-three 72-bit scalable matrix and SafeForge `(8,4,3)` matrix are shortened-Hamming SEC matrices. Large-`r` arbitrary-column equivalence remains undecided, so the claim is deliberately narrower than construction novelty.

## 2. Where does the observed gain come from?

The original small gain comes from physical/data-column mapping and probability-aware syndrome actions within a known `(8,4,4)` code. Exhaustive mapping recovers the generated ordering `[11,14,7,13]`. The SafeForge gain additionally comes from choosing syndrome partitions that support zero-SDC abstaining actions over the expanded error support. It is not attributed to a new algebraic family.

## 3. Reconciled apples-to-apples results

| Strategy | Nominal correct | Nominal DUE | Nominal SDC | Worst DUE at TV 0.1 | Worst SDC at TV 0.1 |
|---|---:|---:|---:|---:|---:|
| Conventional SECDED / fixed Hsiao | 0.48 | 0.52 | 0 | 0.62 | 0.10 |
| Nominal ML / fixed Hsiao | 0.93 | 0 | 0.07 | 0 | 0.17 |
| Robust abstain / fixed Hsiao | 0.11 | 0.89 | 0 | 0.99 | 0 |
| Nominal synthesized H + ML | 0.97 | 0 | 0.03 | 0 | 0.13 |
| Robust co-synthesized H + abstain | 0.64 | 0.36 | 0 | 0.46 | 0 |

The older values `0.0160849`, `0.400766`, and `0.510528` are not directly comparable. The first is one spatial-hotspot PMF and a deeper single-code beam search. The second is a 0.55/0.45 weighted two-regime portfolio result with separate residuals 0.311436 and 0.509947 and a smaller co-search budget. The third applies the same portfolio weights to a different one-general-code baseline. The authoritative pipeline rejects mixed experiment identifiers.

## 4. Nominal and worst-case SDC/DUE

The table reports both failure modes. The nominally synthesized ML strategy has the highest nominal correction, but its SDC grows from 0.03 to 0.13 at TV radius 0.1. Robust co-synthesis retains 0.64 nominal correction and has zero SDC for every distribution on the declared expanded support; its worst DUE is 0.46 at the configured radius. This is a declared availability cost, not hidden inside a combined score.

For the 72-bit synthetic expanded-support study, the deterministic 79-mapping heuristic achieves only 0.0661 nominal correction, 0.9339 nominal DUE, and 0.9839 worst-case DUE at TV radius 0.05, while maintaining zero SDC. This is a negative scaling result: the current strict-support policy is too abstaining to be practically attractive.

## 5. Certified ambiguity radius

At zero allowed SDC, both robust small-code strategies have `delta* = 1.0` for total variation over the declared expanded support—the maximum possible TV radius. Conventional and nominal policies have `delta* = 0` because an arbitrarily small mass shift can reach a modeled SDC vector (or nominal SDC is already nonzero). Structured-interval and geometry-Wasserstein artifacts are independently verified in `reports/safe_decoder_structured` and `reports/safe_decoder_wasserstein`.

The radius does not certify errors outside the support hash. None of these engineering/synthetic radii has a statistical-coverage claim.

## 6. Tight adversarial PMF

For the nominal synthesized strategy at TV radius 0.1, the exact adversary removes 0.1 probability from error `[0,1]` and assigns it to the previously zero-nominal adjacent triple `[0,1,2]`, raising SDC from 0.03 to 0.13. The primal and dual objectives agree with zero gap. The robust strategies have an all-zero SDC loss vector on the declared support, so every feasible PMF—including the nominal PMF emitted by the solver—is worst-case with SDC zero.

## 7. Cost of abstention

Relative to nominal synthesized ML, robust co-synthesis gives up 0.33 nominal corrected probability and introduces 0.36 nominal DUE. On the held-out shifted PMF (TV distance 0.55 but contained in the declared expanded support), it reports 0.74 DUE and zero SDC; nominal synthesized ML reports 0.52 SDC and no DUE. Fixed-Hsiao abstention is safer but much more conservative: 0.895 held-out DUE and zero SDC.

## 8. Hardware overhead

The robust co-synthesized small artifact uses a technology-independent proxy of 14 matrix XOR gates and eight correction entries, versus 20 XOR gates and 15 entries for nominal synthesized ML. Certification adds three control bits and a 128-bit envelope identifier in the emitted interface; abstention primarily removes unsafe correction entries. These are structural counts, not area, power, timing, Yosys/ABC advantage, or physical PPA. Linux CI runs Icarus, Verilator, and Yosys functional/structural checks; no characterized library is present.

## 9. Held-out and literature-derived evidence

The held-out synthetic PMF is fully executed as described above. Primary radiation literature verifies that MCU mass and spatial clustering are real concerns, but no public raw address-level trace with sufficient logical-to-physical mapping was verified. Therefore no bit-exact literature-derived performance number is reported. Aggregate MCU fractions are retained as literature-derived constraints in `data/fault_evidence`, explicitly blocked from being loaded as a fault PMF.

## 10. Scheduler behavior outside the envelope

The scheduler's additive certificate gate marks a mode infeasible before optimization unless ambiguity type, fault regime, support, radius, SDC bound, and certificate ID are valid. The held-out shifted PMF is inside the declared support and TV radius-one envelope, so the specialized robust mode remains eligible and produces zero SDC. A confidence region containing an undeclared error vector fails support containment and selects the detect-only certified fallback. Nominal attractiveness cannot override the gate.

## 11. Exact novelty claim and closest prior work

The claim is a compiler/integration result:

> SafeForge configures or searches a short-block SRAM parity matrix and abstaining syndrome policy under explicit physical distribution uncertainty, emits synthesizable RTL, and attaches a solver-free checkable worst-case SDC envelope used for deployment gating.

This is distinct from, but built on, Hsiao SECDED, MAP/ML and coset-leader decoding, minimax/robust and universal decoding, Wasserstein DRO, and correction masking/miscorrection suppression. It does not claim invention of those foundations or a new code family.

## 12. Unsupported claims and remaining limitations

- No physical PPA, Yosys/ABC optimization advantage, characterized energy, timing, or carbon improvement is claimed.
- No global `k=64` matrix optimum is claimed; the 79-candidate mapping search is a verified heuristic and its DUE result is poor.
- No statistical calibration is claimed for synthetic/engineering ambiguity radii; sample bounds require actual counts and their sampling assumptions.
- No literature-derived bit-exact word PMF or raw radiation trace is available.
- Large-`r` binary-matroid equivalence is not completely decided.
- Certificates cover only the declared finite support and physical ordering.
- The deployment controller/migration datapath is not physically implemented or characterized.
- The previous joint shared-XOR hypothesis remains negative: 369 structural XOR gates versus 350 for independent generation plus shared CSE, with no physical validation.

The scientific outcome is mixed but useful: SafeForge's small exact co-synthesis beats fixed-code abstention on correction/DUE while preserving zero SDC, whereas the current 64-bit heuristic is too conservative. The certificate infrastructure survives either result.
