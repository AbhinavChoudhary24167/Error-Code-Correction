# Portfolio co-synthesis findings

> All fault distributions are modeled synthetic PMFs. XOR counts are structural proxies, not physical area, energy, leakage, or delay.

- Modes: `2` at common `(72,64)` dimensions.
- Weighted modeled residual probability: `0.400766164329`.
- One general generated code weighted residual probability: `0.510528217256`.
- Joint shared-graph XOR proxy: `369`.
- Independent hardware-aware codes followed by shared-graph optimization: `350` XOR proxy gates.
- Naive per-equation XOR proxy: `820`.
- Separately optimized engine XOR proxy: `594` plus `16` output-MUX proxy units.
- Accepted matrix changes during alternating co-synthesis: `3`.
- Ordinary Yosys/ABC baseline: `unavailable`.
- Physical shared-hardware claim: `unsupported_without_synthesis_tool_and_characterized_library`.
- Scheduler integration: `blocked_pending_physical_energy_latency_and_transition_characterization`.

The shared graph is algebraically reconstructed and checked against every matrix row. The joint search is a reliability/hardware Pareto trade-off and did not reduce the XOR proxy relative to independent hardware-aware generation in this run. This is not evidence of PPA improvement: the mandatory ordinary-synthesis baseline and characterized library are absent. Unsafe distribution IDs activate SEC-DED only when that fallback is itself certified; otherwise deployment is rejected.
