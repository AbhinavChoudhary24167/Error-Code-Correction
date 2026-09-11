# Common clock search

The Attempt06 starting point was `T0 = 10.0 ns`. Attempt07 applied it identically to U0 and E0 with 0.10 ns uncertainty, 0.50 ns IO delays and extracted post-route parasitics.

| Candidate | U0 setup/hold | E0 setup/hold | Result |
|---|---:|---:|---|
| T0 = 10.0 ns (100 MHz) | 0 / 0 violations, WNS +4.4610 ns | 0 / 0 violations, WNS +0.591127 ns | tightest tested common period; selected |

No relaxation sweep was justified: the initial common candidate closed setup and hold for both. Residual maximum-transition violations are pin/DRV constraints and would not be removed by increasing the clock period. The achieved common constrained frequency is therefore 100 MHz. Diagnostic period-min/fmax reports are 5.54 ns/180.54 MHz for U0 and 9.41 ns/106.28 MHz for E0; they are not independent operating constraints and are not substituted for the common clock.
