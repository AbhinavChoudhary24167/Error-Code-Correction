# Metric double-count audit

## Findings

| Simultaneous score dimensions | Causal overlap | Disposition |
|---|---|---|
| energy and operational carbon | `C_op = CI_use * E_lifetime` | do not optimize both as independent sustainability objectives under fixed CI |
| area and embodied carbon | area changes gross dies, yield, and die carbon | retain area as engineering diagnostic; lifecycle carbon carries environmental consequence |
| scrub/retry energy and operational carbon | scrub/retry are terms inside lifetime energy | count once in `C_op` |
| reliability and useful service | SDC/DUE/retry determine service outcome | use explicit feasibility/Pareto reliability dimensions; do not add a weighted reliability utility to GSE |
| latency and SLA-qualified useful service | latency may set `I_k=0` | if an SLA is active, avoid counting the same violation again inside a composite score; otherwise keep latency Pareto-separate |
| correction count and EPC | correction causes energy while possibly preserving service | EPC is diagnostic; lifetime energy and service outcomes consume the event model |
| process steps and patterning carbon | patterning steps contribute to wafer carbon | report decomposition, but total wafer carbon includes each step once |
| mask-layer complexity and mask-set NRE | wafer patterning and mask manufacturing are distinct | wafer processing captures exposures/etch/deposition; physical mask-set manufacturing is a separate volume-allocated term |

## Selection policy

The primary scalar contains only useful correct service in the numerator and lifecycle carbon in the denominator. SDC/DUE/timing/physical feasibility are hard constraints only when externally justified; absent defensible thresholds, they remain explicit Pareto axes. Energy, area, process-gas, patterning, and yield values remain decompositions/sensitivity drivers rather than extra weighted terms in the same scalar.
