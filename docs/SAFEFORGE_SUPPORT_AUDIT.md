# SafeForge support and tail-risk audit

## Scope of the certificate

SafeForge certificates are conditional on an ordered, finite set of physical error vectors. The earlier result `delta* = 1` means that a zero-SDC policy remains zero-SDC for every PMF on the declared 28-pattern support. It does **not** mean safety against every nonzero 8-bit error.

The audit executes the emitted syndrome action for every vector and uses four disjoint outcomes:

- **correct**: the systematic data bits equal the transmitted data after execution;
- **DUE**: a nonzero syndrome has no approved correction action;
- **SDC miscorrection**: an approved action leaves incorrect data;
- **undetected**: a zero-syndrome error changes data.

`SDC total` is the sum of SDC miscorrections and undetected errors. A parity-only residual that leaves all data bits unchanged is classified as correct.

## Complete (8,4) enumeration

The audit covers all `2^8 - 1 = 255` nonzero errors. The certified radii below use a zero allowed SDC risk and total-variation ambiguity on the named universe. A radius of zero means either nominal SDC is already nonzero or an arbitrarily small probability shift can reach an SDC vector.

| Decoder | Original 28 | Weight <= 2 (36) | Weight <= 3 (92) | Complete 255 |
|---|---:|---:|---:|---:|
| Conventional minimum-weight, fixed Hsiao | 0 | 1 | 0 | 0 |
| Nominal ML, fixed Hsiao | 0 | 0 | 0 | 0 |
| Robust abstaining, fixed Hsiao | **1** | 0 | 0 | 0 |
| Nominal synthesized matrix | 0 | 0 | 0 | 0 |
| Robust co-synthesized matrix/policy | **1** | 0 | 0 | 0 |

The complete-universe outcome counts make the limitation concrete:

| Decoder | Correct | DUE | SDC miscorrection | Undetected | SDC total |
|---|---:|---:|---:|---:|---:|
| Conventional minimum-weight | 8 | 112 | 120 | 15 | 135 |
| Nominal ML, fixed Hsiao | 14 | 16 | 210 | 15 | 225 |
| Robust abstaining, fixed Hsiao | 3 | 192 | 45 | 15 | 60 |
| Nominal synthesized matrix | 15 | 0 | 225 | 15 | 240 |
| Robust co-synthesized matrix/policy | 8 | 112 | 120 | 15 | 135 |

Thus both `delta* = 1` results are strictly 28-pattern statements. The fixed robust policy encounters six SDC vectors already in the weight-at-most-two universe, while the co-synthesized policy encounters twelve. Neither is universally safe.

## Open-support bound

Let `S` be a certified support, `eta` the actual probability outside `S`, `eta_upper` its upper bound, `R_SDC,S` the conditional within-support bound, and `B_out` an outcome-specific upper bound on SDC outside `S`. For exact `eta`,

```text
P_SDC,total <= (1 - eta) R_SDC,S + eta B_out.
```

When only `eta_upper` is known, the safe endpoint envelope is `R_SDC,S + eta_upper max(0, B_out - R_SDC,S)`. With no outcome-specific proof, `B_out = 1`, reducing to the conservative bound requested in the review. If `eta_upper` is unknown, the only distribution-free complete bound is one; omitted patterns are never assigned zero probability silently. The 8-bit complete enumeration can compute `B_out` exactly as either zero or one for the complement of each named universe and policy.

## 72-bit bounded-weight audit

The streaming audit executes five representative policies on exactly

```text
C(72,1) + C(72,2) + C(72,3) + C(72,4) = 1,091,058
```

vectors.

| Policy | Correct | DUE | SDC miscorrection | Undetected | SDC total |
|---|---:|---:|---:|---:|---:|
| Conventional minimum-weight | 72 | 1,034,356 | 45,304 | 11,326 | 56,630 |
| Nominal ML Hsiao | 170 | 265,328 | 814,234 | 11,326 | 825,560 |
| Fixed Hsiao, zero-SDC declared-support policy | 49 | 833,476 | 246,207 | 11,326 | 257,533 |
| Fixed Hsiao, epsilon=0.1 declared-support policy | 168 | 286,792 | 792,772 | 11,326 | 804,098 |
| Robust-mapping, zero-SDC declared-support policy | 56 | 773,000 | 306,676 | 11,326 | 318,002 |

These counts are not a PMF and are not converted into probabilities. All five policies have SDC vectors in the bounded universe, so their distribution-free within-universe SDC upper bound is one. For errors above weight four the artifact records the symbolic bound

```text
P_SDC,total <= (1 - eta_gt4) R_SDC,weight<=4 + eta_gt4,
```

with `eta_gt4` explicitly unknown and the complete numeric bound therefore equal to one.

## Four distinct robustness claims

- **Within-support robustness**: a verified risk bound for every PMF in an ambiguity set on one explicit finite support.
- **Bounded-weight robustness**: exhaustive execution over all errors through a stated weight; it says nothing about the tail without `eta`.
- **Open-support robustness**: a complete bound combining a support-conditional certificate with an explicit tail-probability bound.
- **Statistically calibrated robustness**: an ambiguity/tail bound derived from samples with stated sampling assumptions and coverage. None of the synthetic or literature-sensitivity radii in this study is statistically calibrated.

## Reproduction artifacts

- `reports/safeforge_hardening/support_audit_8bit.json`
- `reports/safeforge_hardening/weight_le4_72bit_audit.json`
- `reports/safeforge_hardening/result_manifest.json`

Regenerate them with `python scripts/run_safeforge_hardening.py`.
