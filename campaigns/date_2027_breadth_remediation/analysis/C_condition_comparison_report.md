# Workstream C condition-comparison report

The only major changed condition is the implementation clock target: 10 ns historical versus a fresh 5 ns optimization target. Technology, corner, RTL identities, floorplan policy, utilization, placement density, load, activity sequence, and five matched seeds are unchanged.

## Configuration and feasibility

The 5 ns flow uses SKY130HD `tt_025C_1v80` at 1.80 V and 25 C, the frozen ORFS image, 35% utilization, 0.55 placement density, 10 um core margin, 0.05 pF output load, one worker, 10% period-relative I/O delays, a 5,000 ps ABC target, and the exact seeds 11, 13, 17, 19, and 23. The ten routes were implemented fresh in comb-then-pipe order for each seed; no 10 ns database was reused, no retry occurred, and no seed was substituted.

5 ns feasibility is combinational 5/5 and pipelined 5/5. Every point has zero setup violations, nonnegative setup slack, zero hold violations, positive hold slack, completed routing, and zero final DRC. Combinational setup slack spans 0.734417 to 1.00486 ns; pipelined setup slack spans 2.52551 to 2.61827 ns. Request latencies remain one and three cycles, respectively; II remains one for both.

## Within-5-ns matched comparison

| Metric | Comb mean | Pipe mean | Mean paired pipe-vs-comb effect | Ordering |
|---|---:|---:|---:|---:|
| Standard-cell area (um2) | 18,677.40 | 25,535.74 | +36.721138% | pipe higher 5/5 |
| Cell count | 2,077.6 | 2,658.2 | +27.946022% | pipe higher 5/5 |
| Clock buffers | 57.4 | 95.2 | +66.424758% | pipe higher 5/5 |
| Timing-repair buffers | 359.6 | 353.0 | -1.835042% | pipe lower 5/5 |
| Detailed wirelength (um) | 44,863.2 | 50,584.2 | +12.758780% | pipe higher 5/5 |
| Via count | 9,171.0 | 10,878.6 | +18.620922% | pipe higher 5/5 |
| Slack-derived frequency (MHz) | 243.699 | 410.726 | +68.629653% | pipe higher 5/5 |
| Total power (W) | 0.0275524 | 0.0222235 | -19.336606% | pipe lower 5/5 |
| Energy/op (pJ) | 137.775632 | 111.128557 | -19.336606% | pipe lower 5/5 |

## 10 ns to 5 ns condition sensitivity

For the combinational identity, the 5 ns implementation changes mean area by +0.149565%, cell count by +0.115718%, clock buffers by +2.221990%, timing-repair buffers by +0.335196%, detailed wirelength by -0.113854%, slack-derived frequency by +2.048818%, total power by +89.032798%, and energy/op by -5.483601% relative to its matched 10 ns physical identities.

For the pipelined identity, the 5 ns implementation changes mean area by -0.202314%, cell count by -0.127712%, clock buffers by -1.820297%, timing-repair buffers by 0.000000%, detailed wirelength by +1.241451%, slack-derived frequency by +17.368168%, total power by +99.104293%, and energy/op by -0.447853% relative to its matched 10 ns physical identities.

The near-doubling of total power is evaluated over a trace with half the clock period; energy/op remains a separately reconstructed quantity and is not inferred from power ordering alone.

## Ordering and Pareto result

Ordering preservation versus 10 ns: area 5/5; timing 5/5; total power 5/5; energy 5/5.

At 5 ns, the pipeline remains larger and higher-throughput but lower-energy for every seed; each paired relation is non-dominated when area, request latency, energy, and timing are considered. Neither identity becomes infeasible. Thus the evaluated architectural ordering is portable from the 10 ns to the predeclared 5 ns optimization condition, while the magnitudes remain condition-sensitive.

Results are scoped to these evaluated physical identities and deterministic heuristic seeds; no universal operating-point or population claim is made.
