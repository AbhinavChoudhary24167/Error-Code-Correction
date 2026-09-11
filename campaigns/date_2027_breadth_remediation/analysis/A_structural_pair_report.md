# Workstream A structural-pair physical report

## Qualification and structural sanity

The flat and hierarchical Hsiao identities are exact-equivalent with zero temporal alignment, one-cycle request latency, and II=1. Exhaustive SAT proved decoder equality for every arbitrary 72-bit received word with no assumptions. Sequential temporal induction proved same-cycle equality of the complete registered transaction boundary from equal zero initialization under arbitrary reset, valid, payload, and decoder-word sequences.

Under one common SKY130HD mapping policy, the baseline has 1,244 mapped cells, 349 registers, and 350 XOR/XNOR cells; the hierarchical identity has 1,254 mapped cells, 349 registers, and 343 XOR/XNOR cells. Their cell histograms, normalized graph signatures, and mapped-netlist hashes differ. Combinational logic depth is `NOT ASSESSABLE` because the common mapped-library `ltp -noff` report exposed no paths; this absence is not converted to a pass criterion.

## Five matched routes

All ten fresh runs completed and were target-feasible: flat 5/5 and hierarchical 5/5. Every run is joined to its own final ODB/netlist, SDC, SPEF, trace, configuration, source hashes, command, log, and raw-artifact manifest.

| Metric | Flat mean | Hierarchical mean | Mean paired effect | Ordering |
|---|---:|---:|---:|---:|
| Standard-cell area (um2) | 19,190.64 | 19,082.32 | -0.564122% | hierarchical lower 5/5 |
| Cell count | 2,175.4 | 2,181.4 | +0.275904% | hierarchical higher 5/5 |
| Detailed wirelength (um) | 49,810.4 | 51,734.0 | +3.867152% | hierarchical higher 5/5 |
| Via count | 9,718.0 | 10,098.4 | +3.918161% | hierarchical higher 5/5 |
| Slack-derived frequency (MHz) | 212.912 | 218.451 | +2.655651% | hierarchical higher 4/5 |
| Total power (W) | 0.0149554 | 0.0151546 | +1.328395% | hierarchical higher 5/5 |
| Energy/op (pJ) | 149.568951 | 151.561357 | +1.328395% | hierarchical higher 5/5 |

The exact per-seed observations and the required mean, median, sample standard deviation, minimum, maximum, range, absolute difference, paired percentage, and ordering counts are preserved in `A_structural_pair_per_seed.csv` and `A_structural_pair_summary.json`.

## Scoped conclusion

The intended structural distinction survives common synthesis and produces a repeatable, mixed physical displacement: slightly lower routed cell area but more cells, wire, vias, total power, and energy for the hierarchical identity across these five matched heuristic seeds. This is a scientifically valid small-effect result and demonstrates implementation identity beyond the earlier temporal-pipelining transformation. It does not establish a universally preferable structural style.
