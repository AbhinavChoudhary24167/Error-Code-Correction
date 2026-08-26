# DATE 2027 Revision 2 matched-seed protocol

Status: `FROZEN_BEFORE_EXECUTION`

Frozen on 2026-08-25 before any Revision-2 physical result was produced or inspected.

## Purpose

This is a controlled sensitivity experiment over OpenROAD placement/routing heuristics. It is not a sample from a claimed probability distribution and it is not used for population inference.

## Seed rule and frozen set

The seed rule is the first five prime integers greater than or equal to 11. The resulting ordered set is exactly:

```text
11, 13, 17, 19, 23
```

For a run at seed `s`, all three qualified controls are set to the same value:

```text
GPL_RANDOM_SEED=s
GRT_SEED=s
OR_SEED=s
```

The source proof for these variables is the immutable Gate-03F environment manifest and its hashed ORFS source inventory. No seed may be added, removed, substituted, or repeated because of a physical outcome.

## Frozen matrix

The full matrix is predeclared as follows:

| Implementation | Seeds | Runs | Power policy |
|---|---|---:|---|
| SECDED combinational `(72,64)` | 11, 13, 17, 19, 23 | 5 | mandatory no-error trace |
| SECDED pipelined `(72,64)` | 11, 13, 17, 19, 23 | 5 | mandatory no-error trace |
| Hsiao algorithmic `(72,64)` | 11, 13, 17, 19, 23 | 5 | conditional on pre-PPA exact-identity qualification; no-error trace if 10 ns feasible |
| BCH `(78,64,t=2)` syndrome/Chien | 11, 13, 17, 19, 23 | 5 | diagnostic only; no target-clock energy when 10 ns is infeasible |

The unchanged historical BCH route took approximately 26 minutes, so the full five-seed BCH sweep was declared computationally reasonable before any Revision-2 BCH result was inspected. The maximum physical matrix is 20 fresh routes. If Hsiao fails qualification, its five routes are omitted and the matrix contains 15 routes.

## Common implementation policy

All routes use the frozen DATE-final identity except for the explicitly varied seed and the separately qualified Hsiao Revision-2 RTL identity:

- `openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e`;
- ORFS commit `56496f3980fb6e9e58f10c8aea4a98949c0fe5f2`;
- OpenROAD commit `ab6fd26351dc449e69059684dc6aa9ae9046eb36`;
- SKY130HD, `tt_025C_1v80`, 1.80 V, 25 C;
- 10.0 ns clock and 10,000 ps ABC period;
- 10% input delay, 10% output delay, 0.05 pF output load;
- 35% core utilization, aspect ratio 1.0, 10 um margin, placement density 0.55;
- one worker, `LEC_CHECK=0`, and the same SDC methodology;
- independent encoder and decoder channels, II=1, no backpressure;
- the same frozen no-error 100,000-operation SplitMix64 activity trace for every applicable seed.

No per-design or per-seed floorplan, density, timing, or RTL tuning is allowed.

## Run preservation and failures

Every run has a unique `architecture-seed` run ID in `/var/lib/green-ecc-date2027-revision2/`. The runner records the command, effective environment, start/end timestamps, stage exit status, final reports, and a SHA-256 inventory, then makes the run tree read-only. Gate 03F-07 and Gate 04 final namespaces are never reused.

A poor physical result is never retried. An infrastructure failure is preserved. At most one replacement attempt using the same seed may be authorized, and only after documenting why the failure was independent of the implementation result.

## Metrics and analysis

The authoritative run extractor preserves structure/area, setup and hold timing, routing, DRC, power, and energy fields. Timing reports include signed worst setup slack, clipped WNS as a separate field, TNS, violation counts, and a fixed-implementation slack-derived frequency estimate. The latter is not a frequency sweep.

SECDED effects are calculated as matched pairs for area, detailed wirelength, cell count, slack-derived frequency, total power, and no-error energy/op. Each effect reports all five values, mean, median, sample standard deviation, minimum, maximum, and range. No p-values are computed.

Dominance is evaluated per seed, from aggregate means, and conservatively from sensitivity ranges. Latency remains architectural (one versus three cycles) and is not treated as seed-sensitive.
