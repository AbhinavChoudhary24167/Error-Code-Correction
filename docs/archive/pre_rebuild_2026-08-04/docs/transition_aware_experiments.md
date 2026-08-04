# Transition-aware experiment methodology

## Reproduction

```bash
python3 scripts/run_transition_study.py
```

The command validates `configs/transition_schedule.example.json`, regenerates
all ten seeded traces, evaluates every configured physical design and policy,
and writes data, deployment artifacts, SVG figures, takeaways, and hashes to
`reports/transition_aware/`.

## Trace families

The study deliberately does not reconstruct the unavailable 189 scenarios. It
generates and records:

1. stationary SBU operation;
2. stationary MBU operation;
3. one SBU-to-MBU phase change;
4. periodic fault changes;
5. short noisy fault fluctuations;
6. temperature/VDD phases;
7. changing read/write intensity;
8. a grid-carbon phase change;
9. combined fault/workload/environment changes; and
10. uncertain transitions.

Every trace file records generator family, all parameters, seed, epoch duration,
accesses, active words, operating conditions, constraints, and uncertainty.

## Compared policies

- best static ECC across the full trace;
- configured fault-regime lookup;
- per-epoch snapshot oracle that ignores transition cost while deciding;
- greedy current-epoch switching;
- exact transition-aware dynamic programming;
- chance-constrained robust dynamic programming; and
- prediction-horizon hysteresis with dwell, confidence, and rate limits.

The oracle's transition costs are charged after its choices are made. It is a
diagnostic upper bound on snapshot information, not a deployment policy.

## Canonical synthetic findings

All quantities below use synthetic physical-unit sensitivity inputs and must
not be cited as measured or synthesized SRAM results.

- On the long one-time phase change, the shared whole-memory adaptive schedule
  uses SECDED for six epochs and TAEC for six. It costs `1.096282912 J` versus
  `1.20288 J` for the best fixed design: `0.106597088 J` (8.86%) net saving
  from `0.168 J` gross codec/selected-engine saving after `0.04872 J`
  continuing adaptability and `0.012682912 J` transition cost. The complete
  adaptability ratio is 0.3655.
- Its transition break-even horizon is 33,011,224 accesses under the supplied
  inputs. Each phase contains 100 million accesses.
- On the combined trace, three transitions cost `0.033854432 J`; gross saving
  is `0.100804375 J`, continuing adaptability costs `0.03296 J`, and
  `0.033989943 J` (4.64%) remains. The complete adaptability ratio is 0.6628.
- On periodic faults, the snapshot oracle makes seven transitions and costs
  `0.224997472 J`, worse than the `0.16384 J` best fixed design. Exact
  transition-aware scheduling suppresses all seven changes (`0.1712 J` within
  the adaptive design), so joint co-design selects fixed SEC-DAEC.
- On short noisy fluctuations, the snapshot oracle makes ten transitions and
  costs `0.1664576 J`, versus `0.06438 J` for fixed SECDED. Exact scheduling
  suppresses all ten (`0.0679 J` within the adaptive design).
- The 6-by-6 duration/transition sweep contains 22 adaptive and 14 fixed cells,
  demonstrating a conditional break-even boundary rather than a universal
  adaptive winner.
- The best adaptive granularity changes between whole-memory and bank designs.
  Page granularity never wins the configured suite; its metadata/lookup burden
  exceeds its migration advantage here. Word selection is excluded.
- Hysteresis reduces transitions on the periodic, noisy, and uncertain traces,
  but can make one more change than the snapshot policy on several stationary
  or phase traces because the policies start from different safe/fallback
  conditions. H5 is therefore only conditionally supported.
- On the uncertain trace, the best adaptive design is bank-granular, but its
  complete adaptability ratio is 1.0119, so joint co-design retains fixed
  SEC-DAEC. Perturbation tests yield mean epoch-mode agreement 0.6544 and mean
  regret `0.01098 J` for the nominal robust schedule.

## Sweeps and interpretation

The main break-even sweep varies accesses per epoch and transition-energy
multipliers. The multiplier is dimensionless and does not infer a technology
value. Architecture/granularity comparisons use explicitly configured MUX
replication, metadata count, access overhead, leakage, migration size, and
temporary dual-format capacity.

The scalability benchmark varies `T` over 8, 32, and 128 epochs and `M` over 2,
4, 8, and 16 abstract modes. It validates the expected `O(T M^2)` dependence;
wall-clock measurements remain host-dependent.

## Validity boundary

The study is suitable for algorithm correctness, conditional hypotheses,
normalized regime maps, and integration testing. Technology-specific conclusions
require exact-PVT codec/MUX/controller characterization, physical metadata and
routing cost, measured or defensible workload traces, and calibrated migration
energy/latency. Until those inputs exist, absolute energy and carbon savings are
illustrative sensitivity results only.
