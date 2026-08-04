# SafeForge: Certifying SRAM Error Correction Under Fault-Model Uncertainty

## Abstract

Fault-aware syndrome decoding can improve correction on an assumed SRAM fault distribution, but the same specialization can silently corrupt data after distribution shift. SafeForge is an SRAM-oriented certifying compiler that generates syndrome correction/abstention policies, synthesizable RTL, and independently verifiable worst-case SDC bounds under explicit fault-distribution uncertainty. The compiler treats silent data corruption (SDC) and detected uncorrectable error (DUE) as separate risks, emits an adversarial PMF and dual certificate, and gates deployment on support, ambiguity radius, tail probability, certificate integrity, and system SDC policy. Exhaustive `(8,4)` evaluation shows both the benefit and the boundary: nominal policies reach high conditional correction, but the zero-SDC `delta*=1` result holds only on a declared 28-vector support and disappears on broader error universes. At `(72,64)`, fixed established matrices support practical syndrome-level policy compilation and expose an SDC-DUE frontier, while arbitrary matrix co-synthesis remains a negative scalability result. Aggregate radiation and undervolting measurements are represented as structured ambiguity constraints rather than fabricated bit-exact PMFs. The artifact includes solver-independent verification, full bounded-universe audits, synthesizable RTL, generic Yosys/ABC structure, and fail-closed scheduler tests.

## Contributions

1. A certifying compiler for correction-or-abstention syndrome policies under total-variation, structured-interval, and geometry-Wasserstein uncertainty.
2. Solver-independent replay of the matrix, policy, support, primal witness, dual bound, and artifact hashes.
3. An explicit separation of finite-support, bounded-weight, open-support, and statistically calibrated claims, including complete 8-bit and weight-through-four 72-bit audits.
4. A risk-coverage study on fixed SECDED/Hsiao matrices that reports the DUE price of increasing the allowed worst-case SDC budget.
5. A fail-closed deployment gate that rejects unsupported, stale, corrupt, unverifiable, or system-incompatible policies.

The work does not claim a fundamentally new `(8,4)` code, universal safety, practical 64-bit arbitrary-matrix co-synthesis, superior shared hardware, measured silicon behavior, or physical PPA.

## 1. Motivation and claim boundary

Nominal maximum-probability decoding chooses the most likely error in each syndrome class. That choice is reasonable only while the assumed PMF remains valid. When another error in the same class gains mass, the correction itself can turn a detectable event into SDC. SafeForge instead approves a correction only under an explicit risk constraint and abstains otherwise.

The `(8,4)` generated matrix is extended-Hamming/Hsiao-equivalent. Controlled ablations therefore attribute gains to matrix representation only when the decoder and physical placement are held fixed. In this experiment changing the equivalent parity-check representation with a single-bit decoder changes nominal correction by `0`; changing to an unweighted syndrome/coset-leader policy adds `0.45`; the tested PMF specialization adds `0`; and robust physical placement recovers `0.44` correction for the zero-SDC abstaining policy. The headline nominal `0.97` correction is not evidence of a new algebraic code.

## 2. Threat model and certificate semantics

An experiment identity binds dimensions, support hash, nominal PMF, ambiguity configuration, physical ordering, decoder semantics, normalization, and units. Each result additionally carries a matrix ID, decoder-policy ID, PMF ID, parity budget, mapping, universe, ambiguity type/radius, and metric scope.

Nominal and held-out rows are probability partitions: correction + DUE + SDC = 1. Worst-case SDC and worst-case DUE are separate maximizations and need not sum to one. The verifier recomputes the policy loss vector and checks the adversarial PMF, ambiguity feasibility, dual signs/stationarity or closed-form dual, objective tightness, and hashes without calling the optimization solver.

## 3. Complete small-code audit

On the declared 28-vector support, the fixed-code and co-synthesized robust policies have zero SDC for every PMF and hence TV `delta*=1`. On all 255 nonzero errors, their SDC totals are respectively `60/255` and `135/255`, so the corresponding zero-SDC radius is zero. The complete enumeration is the decisive negative result: certification is support-conditional, not universal. Tail risk is lifted with

```text
P_SDC,total <= (1-eta) R_SDC,S + eta B_out,
```

where `B_out=1` unless a tighter outcome proof exists. See `docs/SAFEFORGE_SUPPORT_AUDIT.md`.

## 4. Practical fixed-code `(72,64)` decoding

SafeForge retains 64-bit matrix co-synthesis as a failed scalability result and compiles policies over the 255 nonzero syndrome classes of fixed matrices. Dimension-matched conventional extended-Hamming SECDED, Hsiao SECDED, three existing generated matrices, and the existing robust physical mapping are evaluated. No verified dimension-matched SEC-DAEC matrix is present. The modeled TAEC wrapper reuses SECDED and has an adjacent-triple/single-error collision. The checked-in BCH example is `(63,51)` and its demonstrated triple collision means it is not used as verified BCH evidence.

At TV radius `0.05`, fixed Hsiao with zero allowed SDC corrects `0.0394` nominal mass and has `0.9606` nominal DUE and worst-case DUE `1.0`. Allowing worst-case SDC `0.05` raises correction to `0.3828` and lowers worst-case DUE to `0.6672`; an `epsilon=0.1` configuration achieves `0.4774` correction, nominal DUE `0.4864`, worst-case SDC `0.0861`, and worst-case DUE `0.5364`. The robust physical mapping follows a similar frontier. The existing generated spatial matrix reaches `0.9839` nominal correction and `0.0661` worst-case DUE at `epsilon=0.05`, but its zero-SDC point is infeasible at this radius.

These are certified feasible, achieved operating points produced by the frozen deterministic syndrome-class compiler rule; no global frontier-optimality claim is made. No preferred epsilon is selected because the repository has no system reliability requirement from which to derive one.

## 5. Aggregate experimental evidence

Primary alpha/neutron/voltage studies report device-specific aggregate facts but not reusable 72-bit logical error traces. SafeForge retains each source separately. Examples include a lower bound above `0.15` on multicell-upset fraction below 550 mV in a 5-nm SRAM alpha experiment, a `0.0559` to `0.277` cross-device FPGA neutron MCU sensitivity range, and a greater-than-`0.90` correctable/single-bit aggregate in an undervolted FPGA BRAM study. These become linear constraints over multiplicity categories. They are not pooled, are not sampling confidence intervals, and are not called measured bit-exact PMFs.

The literature-constrained evaluations are deliberately mixed. Under the broad 5-nm alpha aggregate, the nominal and nonzero-risk policies can have worst-case SDC `1`; the support-universal zero-SDC policy remains SDC-free but has worst-case DUE `1`. All emitted structured certificates pass the solver-independent verifier. This is useful external sensitivity evidence, not silicon validation of SafeForge.

## 6. Hardware evidence

The RTL runner records exact Icarus, Verilator, and Yosys/ABC commands, logs, versions, and exit codes. The small campaign crosses all 16 data words with 28 modeled errors (448 checks); the 72-bit campaign crosses 427 modeled errors with four linearity representatives (1,708 checks). TAEC and BCH regressions explicitly preserve their collision cases as negative tests.

On the same 72-bit matrix and physical mapping, generic ABC mapping reports 311 cells and a longest topological path of 38 cells for the nominal policy, versus 380 cells and 40 cells for the robust policy with envelope controls. Both have the same 240-gate syndrome XOR proxy; the nominal policy has 171 correction entries and the robust policy 56. These are generic structural results. There is no characterized library, so the paper makes no area, delay, energy, leakage, or physical-PPA claim.

## 7. Deployment rule

A specialized policy is eligible only if the observed fault regime maps to its support, the ambiguity radius is inside its envelope, the out-of-support probability upper bound is present and below its certified tail limit, the certificate version/hash/integrity and independent verification all pass, and its SDC limit satisfies system policy. Otherwise the scheduler may use only a separately certified fallback; if none is feasible it reports no safe mode. Boundary, rejection, stale, corrupt, unknown-support/tail, and no-fallback paths are tested.

## 8. Positive and negative findings

Positive findings are that syndrome-policy specialization can materially improve nominal coverage; abstention makes worst-case SDC independently certifiable; fixed `(72,64)` matrices avoid arbitrary-matrix search; and the complete tool chain emits checkable software, RTL, and scheduler artifacts.

Negative findings are equally central. The strongest small-code radius is support-conditional. Bounded-weight execution reveals many SDC vectors outside the declared model. Zero-SDC fixed-code decoding can impose impractical DUE. The 64-bit arbitrary-matrix search is not a practical or globally optimal co-synthesis result. Published aggregates do not establish a bit-exact PMF. The TAEC/BCH examples do not validate their advertised correction strengths. Generic synthesis is not physical characterization.

## 9. Artifact map and reproduction

- hardening study: `python scripts/run_safeforge_hardening.py`
- hardware validation: `python scripts/run_safeforge_hardware_validation.py`
- required regression: `make`, `make test`, `python3 -m pytest -q`
- results: `reports/safeforge_hardening/` and `reports/safeforge_hardware_validation/`
- evidence provenance: `data/fault_evidence/sources.json`

The novelty scope is frozen. Remaining work requires new measured traces, a characterized library, or an explicit system risk requirement; those inputs would extend evidence, not change the contribution.
