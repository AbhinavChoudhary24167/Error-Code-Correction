# DRV repair sequence

All candidate swaps were first evaluated non-persistently against the frozen Attempt07 seed-11 ODB/SDC/SPEF. The accepted common decision rule is: resize a legal external driver only when constrained STA proves the target row closes; never edit macros or constraints. U0 had no target satisfying that rule. E0 received three legal replacements before global routing, followed by ordinary detailed placement and routing.

| Repair | Reason | Rows before -> after | Candidate result |
|---|---|---:|---|
| `_513_`: `xnor2_1` -> `xnor2_2` | Class-A fanout/RC driver | 3 -> 0 | 0.646700442 -> 0.394375741 ns |
| `din[56]` driver: `buf_4` -> `buf_8` | Long extracted route to macro input | 1 -> 0 | 0.367528468 -> 0.226246253 ns |
| `din[57]` driver: `buf_4` -> `buf_8` | Long extracted route to macro input | 1 -> 0 | 0.393737197 -> 0.243002206 ns |

Applied together, E0 goes 80 -> 75 rows. Setup remains 0 violations (WNS 0.591127 -> 0.584552 ns), hold remains 0 (worst slack 0.000901557 -> 0.00122125 ns), route DRC/capacitance/antenna remain 0, standard-cell area changes by 20.1 um^2, total placed area by 20 um^2, wirelength by 24 um, vias by 4, and vectorless estimated power by 1.96e-06 W. Legalization moved 5.4 um total/max with 0% HPWL change in the canonical repair log.

Rejected experiments are also preserved. A `clkbuf_16` on data `rstb` only improves 0.615880728 -> 0.602424264 ns; ECC `rstb` reaches 0.351614386 ns at best, still above 0.351; alternative data-clock `buf_16`/`bufbuf_16` cells worsen 0.511382282 ns to 0.519892454/0.519068480 ns. None was applied. No per-seed tuning occurred.
