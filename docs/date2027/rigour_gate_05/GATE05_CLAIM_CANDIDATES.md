# Gate 05 claim candidates

No Pareto frontier, GREEN Score, NSGA-II result, or final ECC selection is produced here.

## STRONG

1. **Microarchitectural realization materially changes physical cost for identical coding semantics.** Gate 03R proves the combinational and pipelined SECDED implementations universally equivalent after temporal alignment. At the frozen 10 ns point, pipelining changes area by +36.702%, Fmax by +45.911%, detailed wirelength by +12.067%, and no-error power/steady-stream energy per useful operation by -24.016%, while nominal latency rises from one to three cycles and initiation interval remains one.
2. **The common target exposes implementation feasibility differences hidden by algorithm-level capability.** The evaluated BCH RTL completes routing with zero DRC but has WNS -4.78052 ns and achieved Fmax 67.6566 MHz, so it cannot meet the common 100 MHz target under this implementation, technology, corner, and physical policy.

## SUPPORTED

1. **Reliability capability alone is insufficient for selection.** The evaluated BCH implementation corrects every weight-1 and weight-2 mask in its proven universe, but incurs +207.356% area and +310.975% detailed wirelength relative to combinational SECDED and misses 10 ns. This is an implementation-scoped conclusion, not a universal BCH claim.
2. **Beyond-guarantee behavior differs among validated codes.** Under exhaustive canonical-coordinate weight-3 observation, SDC fractions are 809/1065 for conventional SECDED, 2847/4970 for Hsiao, and 265/1463 for BCH. These are finite-universe observations, not field-weighted SDC rates or weight-3 correction guarantees.
3. **Hsiao remains reliability-qualified but not cross-layer complete.** Its weight-3 reliability observation is usable, while `PPA_UNAVAILABLE` prevents it from becoming a full point in a future PPA-dimensional analysis.

## WEAK

1. **Error-class power differs numerically.** Full-precision OpenSTA estimates resolve small class differences, but Gate 05 has no evidence that those differences are practically significant or representative of field error frequencies.

## UNSUPPORTED

1. Any FIT, SER, operational fault-rate, or physical interleaving superiority claim.
2. Any claim that BCH as a family cannot operate at 100 MHz.
3. Any Hsiao area, timing, power, energy, or Pareto-dominance claim.
4. Any claim that the 10 ns BCH energy estimate is achievable 100 MHz operating energy.
5. Any final best-ECC selection, Pareto-frontier membership, GREEN Score, or NSGA-II result.
