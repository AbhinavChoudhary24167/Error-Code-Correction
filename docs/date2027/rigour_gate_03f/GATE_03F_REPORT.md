# DATE 2027 Gate 03F qualification verdict

`GATE_03F_PASS`

`GATE_04_READY`

Seven immutable physical runs were evaluated: three GCD, two representative conventional SECDED (72,64), and two BCH (78,64,t=2). All used the frozen image, SKY130HD corner, 10.0 ns clock, constraints policy, placement settings, seed 11, and one OpenROAD worker.

## Adjudication

- provenance_pinned: `PASS`
- exactly_seven_unique_runs_present: `PASS`
- all_runs_complete_normally: `PASS`
- logical_behavior_valid: `PASS`
- routing_and_drc_consistent: `PASS`
- area_cell_utilization_wirelength_stable: `PASS`
- timing_and_fmax_stable: `PASS`
- noise_small_enough_for_meaningful_ecc_comparison: `PASS`

## Power

`ACTIVITY_BASED_POWER_QUALIFIED`

Power is nonblocking for Gate 03F. When qualified, values are post-route OpenSTA estimates from deterministic 100,000-operation VCDs for no-error, single-error, and double-error activity. No arbitrary toggle rate or field-rate weighting is used. Energy per useful operation is total trace energy divided by exactly 100,000 useful transactions.

## Frozen interpretation policy

> A comparative ECC effect will be interpreted quantitatively only when its magnitude is at least 5× the measured reproducibility noise for that metric.

Noise is the observed repeated-run range in each metric's own units. Every report also retains the sample standard deviation, coefficient of variation, extrema, range, and maximum relative run-to-run difference. Zero observed variation is reported as zero; no positive tolerance is invented.
