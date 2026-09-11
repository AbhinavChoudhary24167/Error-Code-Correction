# Attempt08 matched final-route comparison

Canonical seed 11 was recomputed from fresh final ODB/DEF/GDS/SPEF results after the common repair policy. No Attempt07 physical metric is reused as an Attempt08 result.

| Metric | U0 | E0 | E0 - U0 |
|---|---:|---:|---:|
| Macro area (um^2) | 201267 | 260332 | 59065 |
| Standard/physical-cell area (um^2) | 5566.59 | 15438.6 | 9872.01 |
| Total placed area (um^2) | 206833 | 275770 | 68937 |
| Core / die area (um^2) | 439734 / 470000 | 615628 / 650000 | — |
| Wirelength (um) | 22186 | 79769 | 57583 |
| Vias | 1084 | 6690 | 5606 |
| Clock buffers / inverters | 0 / 0 | 3 / 1 | — |
| Setup WNS/TNS (ns) | 4.46099 / 0 | 0.584552 / 0 | — |
| Worst hold slack (ns) | 0.0249489 | 0.00122125 | — |
| Vectorless post-route power (W) | 0.00080451 | 0.00197643 | 0.00117192 |

Repair displacement versus Attempt07 is U0: 0 um^2 cells, 0 um wire, 0 vias, and 0 W. E0: 20.1 um^2 cells, 24 um wire, 4 vias, and 1.96e-06 W. Power remains `COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE`; energy/access remains `NOT_QUALIFIED`.
