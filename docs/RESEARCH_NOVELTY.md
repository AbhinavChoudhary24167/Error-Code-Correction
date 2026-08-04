# Research novelty and claim boundary

## Central question

> Under what operating conditions, workload horizons, fault transitions, and
> hardware overheads is changing ECC modes better than retaining one fixed ECC?

GREEN-ECC answers this conditional question by treating protection as an
ordered scheduling and architecture co-design problem. It does not assume that
the ECC preferred in one snapshot should be installed in the next epoch.

## Testable hypotheses

- **H1 — adaptation paradox:** independently minimizing every epoch can cost
  more than one static ECC after migration and continuing adaptability costs.
- **H2 — break-even horizon:** a finite workload horizon separates beneficial
  and harmful switching whenever net per-access improvement is positive.
- **H3 — architecture regime:** the preferred fixed, parallel, gated-parallel,
  or shared design changes with epoch duration and transition frequency.
- **H4 — granularity regime:** bank/page selection helps only while reduced
  migration exceeds replicated metadata, lookup, fan-out, and MUX overhead.
- **H5 — robust hysteresis:** uncertainty-aware benefit margins suppress unsafe
  or low-value changes with bounded regret relative to the offline optimum.

The executable default study labels all mode and hardware values
`synthetic_sensitivity`. It can support or reject these hypotheses only within
that declared experiment—not for a fabricated technology implementation.

## Closest primary approaches

| Approach | What it establishes | Optimization/control emphasis | Physical ECC transition cost in the available evidence | Difference in this GREEN-ECC revision |
|---|---|---|---|---|
| Shin et al., *Adaptive ECC for Tailored Protection of Nanoscale Memory*, IEEE Design & Test 34(6), 2017, DOI [10.1109/MDAT.2016.2615844](https://doi.org/10.1109/MDAT.2016.2615844) | Reconfigurable ECC for run-time protection in nanoscale memory | Variable protection strength | The verified abstract establishes reconfiguration, but is insufficient to verify complete trace scheduling with migration and dwell cost | Optimizes an ordered ECC schedule and exposes all missing transition terms |
| Luo et al., *Using ECC DRAM to Adaptively Increase Memory Capacity (CREAM)*, HPCA 2018, [arXiv:1706.08870](https://arxiv.org/abs/1706.08870) | Multiple reliability/capacity layouts and region-aware hardware support | Capacity and reliability adaptation | Layout and controller overhead are evaluated; the paper is not used here as evidence of a migration-cost-aware ECC sequence optimizer | Separates snapshot benefit from sequence-level transition cost and remaining horizon |
| Wu et al., *An Adaptive Thermal-Aware ECC Scheme for Reliable STT-MRAM LLC Design*, IEEE TVLSI 27(8), 2019, DOI [10.1109/TVLSI.2019.2913207](https://doi.org/10.1109/TVLSI.2019.2913207) | Temperature-dependent ECC-strength adaptation (Chameleon) | Thermal reliability, performance, and energy | Hardware overhead is studied; available metadata does not verify offline trace DP with migration break-even | Adds explicit transition matrices, dwell history, safe abstention, and architecture selection |
| Stefani et al., *DEMC: A Dynamic Multi-ECC Memory Controller with Per-Block Adaptation*, Integration 109, 2026, DOI [10.1016/j.vlsi.2026.102728](https://doi.org/10.1016/j.vlsi.2026.102728) | Per-block ECC response to monitored error rate with controller synthesis | Online error-rate-based code selection | The published abstract/method preview reports dynamic operation and synthesis; a full-trace transition-cost scheduler is not established by the accessible evidence | Evaluates static, lookup, oracle, greedy, hysteretic, exact, and robust schedules on the same trace |
| Benini, Bogliolo, and De Micheli, *A Survey of Design Techniques for System-Level Dynamic Power Management*, IEEE TVLSI 8(3), 2000, DOI [10.1109/92.845896](https://doi.org/10.1109/92.845896) | State transitions, workload dependence, and break-even reasoning are established system-level power-management ideas | Dynamic power-state policy | Not ECC-specific | Applies transition-aware reasoning to ECC re-encoding, protected format metadata, and reliability constraints |
| Gupta et al., *ACT: Designing Sustainable Computer Systems with an Architectural Carbon Modeling Tool*, ISCA 2022, DOI [10.1145/3470496.3527408](https://doi.org/10.1145/3470496.3527408) | Architectural lifecycle-carbon modeling | Operational and embodied carbon | Not an ECC switching scheduler | Keeps lifecycle-carbon terms explicit and applies the same break-even discipline to adaptability |

The closest literature verifies that adaptive ECC, reconfigurable protection,
per-region reliability, dynamic power management, and lifecycle carbon are all
established. Generic dynamic programming is also established. GREEN-ECC must
therefore not claim any of those components alone as novel.

## Focused contribution

The research contribution is the combination of three connected elements:

1. **Transition-aware ECC scheduling.** For each fixed physical design, an
   exact dynamic program minimizes lifecycle energy or carbon across an ordered
   trace after reliability, latency, area, safety, dwell, and switch-count
   constraints are applied.
2. **Break-even analysis for ECC adaptability.** Symbolic functions distinguish
   finite, immediate, never-beneficial, uncharacterized, and infeasible cases.
   The reported ratios compare complete overhead with gross trace benefit; they
   are not ranking scores.
3. **ECC–architecture–granularity co-design.** A topology and granularity are
   selected once as a physical implementation. The ECC may then vary only
   within the modes supported by that implementation. This prevents the
   physically invalid interpretation that topology changes freely every epoch.

## Verified claims

- The basic exact scheduler implements the recurrence
  `D[t,m] = c[t,m] + min(D[t-1,m'] + s[m',m])` and is tested against brute-force
  enumeration.
- Minimum dwell and switching-rate constraints are handled by extending the DP
  state; the unrestricted recurrence is `O(T M^2)`.
- Asymmetric, forbidden, zero-cost, and uncharacterized transitions are
  represented explicitly.
- Generated traces record family, parameters, and seed. Ten transparent trace
  families are provided.
- The deployment rule switches only when forecast benefit exceeds transition,
  continuing overhead, a benefit margin, and uncertainty margin.
- The reference RTL sequences quiesce, old-format read, decode, re-encode,
  write, verify, protected-mode commit, resume, and recovery handshakes.
- The example suite reproducibly contains cases in which a snapshot oracle
  switches repeatedly and becomes worse than the best fixed design after its
  transition costs are charged.

## Claims that must not be made yet

- “First,” “unique,” or universally novel transition-aware ECC system.
- Universal optimality across unmodeled ECCs, technologies, workloads, or fault
  distributions.
- Measured, synthesized, silicon-validated, 14/16 nm, or PVT-characterized
  adaptive overhead.
- Technology-specific energy/carbon savings from the example configuration.
- A complete migration datapath: the RTL is a verified control sequencer, not a
  memory-copy/re-encoding engine.
- Forecast accuracy, online optimality, or real-workload benefit from the
  synthetic traces.
- That page- or word-level selection is practical without corresponding
  physical metadata, routing, lookup, and reliability characterization.

The valid claim is conditional: given a trace, candidate modes, a realizable
architecture, complete cost providers, constraints, and uncertainty bounds,
GREEN-ECC determines whether a transition-safe change has positive lifecycle
value.
