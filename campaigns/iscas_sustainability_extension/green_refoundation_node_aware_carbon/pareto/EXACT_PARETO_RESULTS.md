# Exact Pareto result

The 14 GREEN matrix v2 rows were enumerated exactly with the non-duplicative
objectives `GCI`, physical `SDC`, physical `DUE`, and service `latency_ns`, all
minimized. Zero rows contain those four objectives with an admissible result
qualification, so the eligible set and frontier are both empty. This is a
computed qualification result, not evidence that the architectures are equal.

Logical fault-mask fractions were deliberately excluded: they are exhaustive
or finite functional controls, not a calibrated physical event distribution.
Likewise, diagnostic tool power was not substituted for operational energy or
lifecycle carbon. NSGA-II was not used because the current space is enumerable.

No ECC winner is identified.
