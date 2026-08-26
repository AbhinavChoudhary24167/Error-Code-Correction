# Revision-2 timing and frequency-semantics audit

Verdict: `TIMING_VALUES_VALID_TERMINOLOGY_CORRECTED`

## Exact producer trace

The three Revision-1 frequency values were not calculated from the manuscript's clipped `wns_ns` field.

The authoritative producer chain is:

1. pinned ORFS `/OpenROAD-flow-scripts/flow/scripts/report_metrics.tcl` calls `report_clock_min_period -include_port_paths` and then `report_fmax_metric`;
2. `report_fmax_metric` writes the per-clock and aggregate metrics `finish__timing__fmax__clock:clk_i` and `finish__timing__fmax` into `6_report.json`;
3. `scripts/gate04_final/analyze_results.py:147` reads `finish__timing__fmax` and divides hertz by `1e6`;
4. the manuscript builder copied that field under the historically named `achieved_fmax_mhz` key.

The immutable raw reports establish the following exact lineage:

| Implementation | Signed worst setup slack (ns) | Clipped WNS (ns) | ORFS minimum period (ns, display) | Raw `finish__timing__fmax` (Hz) | Historical value (MHz) |
|---|---:|---:|---:|---:|---:|
| SECDED combinational | +5.89964 | 0 | 4.10 | 2.43881e8 | 243.881 |
| SECDED pipelined | +7.18982 | 0 | 2.81 | 3.55849e8 | 355.849 |
| BCH `(78,64,t=2)` | -4.78052 | -4.78052 | 14.78 | 6.76566e7 | 67.6566 |

The signed worst setup slack is the raw `finish__timing__setup__ws` field. Historical analysis deliberately defined conventional WNS as `min(0, signed_slack)`, which clips positive slack to zero. Therefore substituting clipped WNS into the manuscript equation would incorrectly yield 100 MHz for both timing-feasible SECDED routes.

## Correct prospective notation

Revision 2 uses

```text
s_setup = signed worst setup slack
f_slack = 1000 / (T_target - s_setup) MHz
```

for `T_target` and `s_setup` in ns. Applied to the immutable values, this reproduces the ORFS metrics to their reported precision:

```text
1000 / (10 - 5.89964) = 243.881 MHz
1000 / (10 - 7.18982) = 355.849 MHz
1000 / (10 - (-4.78052)) = 67.6566 MHz
```

Revision-2 machine-readable results call the derived field `slack_derived_frequency_mhz` and preserve the independent raw field `orfs_reported_fmax_mhz` for traceability. `wns_ns` remains a separately reported, conventionally clipped quantity.

## Claim boundary

`f_slack` is a post-route, slack-derived frequency estimate for the fixed implementation optimized under the 10 ns constraint. It is not an experimentally searched maximum frequency and it is not a separately re-optimized implementation at the derived period. Revision 2 therefore does not use `achieved Fmax`, `measured Fmax`, or language implying a period sweep.

The audit changes terminology and producer attribution only. It does not change any underlying historical timing value.
