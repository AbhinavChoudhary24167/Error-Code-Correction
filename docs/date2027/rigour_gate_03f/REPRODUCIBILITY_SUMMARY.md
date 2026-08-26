# Gate 03F reproducibility and power summary

Verdict: `GATE_03F_PASS`

Next state: `GATE_04_READY`

Power: `ACTIVITY_BASED_POWER_QUALIFIED`

All seven runs completed normally, produced the required final physical artifacts, completed routing, and reported zero final DRC and zero flow errors. The three GCD, two SECDED, and two BCH run directories are distinct, read-only, and protected by per-run raw-artifact SHA-256 inventories under `/var/lib/green-ecc-date2027-final/runs`.

## Primary physical metrics

| Design | Replicates | Std-cell area (um2) | WNS (ns) | TNS (ns) | Worst slack (ns) | Achieved Fmax (MHz) | Cell count | Utilization | Detailed wirelength (um) | Final DRC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GCD | 3 | 3,079.2 | 0 | 0 | 5.21700 | 209.0740 | 365 | 48.2171% | 5,845 | 0 |
| Representative SECDED (72,64) | 2 | 18,644.1 | 0 | 0 | 5.89964 | 243.8810 | 2,074 | 49.4984% | 44,609 | 0 |
| BCH (78,64,t=2) | 2 | 57,303.7 | -4.78052 | -309.445 | -4.78052 | 67.6566 | 7,129 | 54.3595% | 183,332 | 0 |

The BCH design consistently does not meet the frozen 10 ns target. That result is a valid, repeated characterization: both runs report the same WNS, TNS, and achieved Fmax. It is not treated as a qualification failure because the flow completes normally and the measurements are stable.

## Secondary metrics

| Design | Buffer count | Clock buffers | Timing-repair buffers | Sequential cells | Routing completion |
|---|---:|---:|---:|---:|---|
| GCD | 64 | 7 | 57 | 35 | PASS |
| Representative SECDED (72,64) | 415 | 56 | 359 | 349 | PASS |
| BCH (78,64,t=2) | 1,843 | 54 | 1,789 | 367 | PASS |

The machine-readable results additionally retain global-route wirelength, global-route congestion violations, detailed-route via count, routed signal-net count, and final flow-error count.

## Measured noise

For every repeated physical metric, including the primary and secondary metrics, the observed values are identical across replicates. Therefore:

- sample standard deviation: `0`;
- range: `0`;
- maximum relative run-to-run difference: `0`;
- coefficient of variation: `0` for nonzero-mean metrics;
- coefficient of variation: `UNDEFINED_ZERO_MEAN` for repeated all-zero metrics such as DRC, WNS where timing is met, and TNS where timing is met.

Zero observed variation is reported directly. No nonzero tolerance is inferred. The complete per-metric mean, sample standard deviation, coefficient of variation, minimum, maximum, range, maximum relative difference, and 5x noise thresholds are in `REPRODUCIBILITY_STATISTICS.json`.

## Activity-based power

Values below are identical across the two physical replicates and, at the tool's JSON precision, across the no-error, single-error, and double-error traces within each design.

| Design | Activity classes | Internal (W) | Switching (W) | Leakage (W) | Total (W) | Energy/useful operation (pJ) | Direct VCD pins | Initially unannotated pins |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Representative SECDED (72,64) | no/single/double error | 0.00679 | 0.00779 | 7.30e-9 | 0.0146 | 146.0146 | 139 | 4,705 |
| BCH (78,64,t=2) | no/single/double error | 0.425 | 0.424 | 2.36e-8 | 0.849 | 8,490.849 | 145 | 16,960 |

These are post-route OpenSTA estimates from deterministic primary-input VCD activity propagated through the final extracted design. They are not silicon measurements. Each trace contains 100,000 useful operations at 10 ns. Energy per operation is `power_W * total_trace_time_ps / 100000`, so reset and drain intervals are included consistently. No arbitrary toggle rate or field-error-rate weighting is used.

## Frozen interpretation policy

> A comparative ECC effect will be interpreted quantitatively only when its magnitude is at least 5× the measured reproducibility noise for that metric.

The noise magnitude is the repeated-run range in the metric's own units. Since every observed range is zero here, a future effect must be nonzero; no positive minimum is invented after seeing the result.
