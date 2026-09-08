# Common hold policy

Attempt08 E0 seed 17 had one hold violation at −0.000169975 ns. Attempt09 first evaluated unbalanced-clock and no/zero-margin repairs; both produced hold failures and are preserved under `raw/rejected_runs`. A common 20 ps post-interface hold-repair margin fixed seed 17 but yielded only 2/5 hold-clean seeds (seed 13 −0.00000272005 ns, seed 19 −0.000328404 ns, seed 23 −0.00484013 ns). A 30 ps worst-seed trial closed hold but reduced seed-23 setup WNS to 0.0214699 ns and increased area, so it was rejected. The retained physically standard policy is:

`repair_timing -setup_margin 0 -hold_margin 0.025 -repair_tns 100 -match_cell_footprint`

It is applied after the fixed interface ECO identically to every E0 seed; there is no seed-specific branch or tuning.

| Seed | Hold violations | Worst hold slack (ns) | Setup violations | Setup WNS (ns) |
|---:|---:|---:|---:|---:|
| 11 | 0 | 0.009414080 | 0 | 0.611109000 |
| 13 | 0 | 0.002310370 | 0 | 0.433227000 |
| 17 | 0 | 0.004361120 | 0 | 0.126462000 |
| 19 | 0 | 0.012037800 | 0 | 0.625476000 |
| 23 | 0 | 0.002597030 | 0 | 0.067940300 |

Final E0 hold-clean robustness is 5/5. Seed 17 finishes with 0 violations and 0.004361120 ns worst slack.
