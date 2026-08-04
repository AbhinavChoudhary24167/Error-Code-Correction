# Decisive SafeForge report

1. **Exact scientific claim supported.** For the fixed conventional `(72,64)` Hsiao matrix, a 427-vector synthetic universe, TV radius 0.05, and 87 declared placements, exact joint and sequential optimization both attain zero modeled-support SDC and worst-case DUE `0.9810098870744284`; the library optimality gap is zero. No claim extends beyond that domain.
2. **Strongest baseline.** Placement-only syndrome-collision isolation followed by exact policy optimization. It selects the same even/odd interleave and exactly matches joint optimization.
3. **System-derived SDC target.** The named server engineering point is 1 system SDC FIT under 1000 relevant system event FIT. Total conditional SDC is at most 0.001; with `eta=1e-5` and tail SDC bound one, modeled-support epsilon is `0.0009900099000990008`.
4. **DUE reduction.** Joint improves worst-case DUE by `0.018990112925571623` absolute versus fixed-placement policy-only (`1.0` to `0.9810098870744284`) and by exactly `0.0` versus the strong sequential baseline.
5. **Held-out validation.** No experimental held-out validation exists. Three nonretuned synthetic holdouts have SDC `0.01875`, `0.234375`, and `0.13194444444444445`, all far above the target.
6. **Tail treatment.** Tail risk is `(1-eta) p_support + eta b`. The declared `eta=1e-5,b=1` projects the zero-support-SDC policy to 0.01 system FIT; an unbounded tail fails closed at 1000 FIT. The tail bound is not empirical.
7. **Area/delay/energy overhead.** Unknown for the decisive policy. Earlier different-policy generic synthesis reported 311 versus 380 cells and depths 38 versus 40, but no characterized area, timing, power, leakage, routing, or energy may be inferred.
8. **Proof and certificate scope.** Exact TV zero-SDC decomposition, independent loss/action replay, solver-free TV primal/dual checks, and zero placement-library gap. Scope excludes other permutations, movable parity bits, unseen errors, and tail probability.
9. **Strongest negative result.** Joint co-design adds nothing over strong sequential placement and still leaves 98.1% worst-case DUE; synthetic unseen shifts introduce large SDC.
10. **Remaining evidence for an archival submission.** Raw bit-exact multi-device/voltage/source traces with layout mapping and licenses; confidence-bounded event FIT and tail; preregistered heldouts; characterized Liberty/STA and placed routing for the exact policy; activity-based power/energy; and memory-macro/interface overhead.

The scientific gate fails. The defensible next paper is a negative boundary study about support completeness and certified availability, not a positive production-deployment claim.
