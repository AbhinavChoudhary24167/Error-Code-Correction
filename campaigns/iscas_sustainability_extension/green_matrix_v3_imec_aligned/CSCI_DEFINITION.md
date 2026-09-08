# Correct-Service Carbon Intensity (CSCI)

For one declared boundary and scenario,

`N_correct = N_req × Q_correct`

`CSCI = C_LC / N_correct`.

Its unit is `kgCO2e / correct service`.  A publication may scale the numerator
and denominator, for example `gCO2e / 10^12 correct services`, provided the
conversion is explicit.

For differing payload widths,

`CSCI_bit = C_LC / (B_payload × N_req × Q_correct)`

with unit `kgCO2e / correct payload bit`.

`N_req` counts external requests, not internal retries or scrubs.  `Q_correct`
credits normal, corrected, and retried responses only when the declared policy
delivers a correct response within its SLA.  It excludes SDC and unrecovered
DUE/timeout.

CSCI is evaluated only after reliability and service feasibility.  It is not a
substitute for SDC/DUE/latency constraints.  Every value carries a system
boundary, payload, workload, policy, lifetime, evidence class, and uncertainty
description.  Missing carbon or service probability blocks the result.  Zero
correct service makes it undefined; no epsilon floor is used.
