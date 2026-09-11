# Functional unit

The primary functional unit is:

> one correct payload-bit memory service delivered under the declared workload and service policy.

The implementation-facing equivalent is one correct payload memory transaction completed under that timing/reliability policy.

For transaction `k`, let `B_k` be useful payload bits and `I_k` be one only if the requested useful service is delivered correctly. If and only if an external latency/SLA limit `L_max` is declared, `I_k=1` additionally requires `latency_k <= L_max`. No latency limit is invented by this campaign.

\[
S(c,\theta)=\mathbb{E}\left[\sum_k B_k I_k\right].
\]

For fixed payload `B`, transaction count `N`, and mutually exclusive outcome model, `S=B N Q`, where

\[
Q=P(SUCCESS\_NORMAL)+P(SUCCESS\_CORRECTED)+P(SUCCESS\_AFTER\_RETRY).
\]

`DETECTED_FAILURE`, `SILENT_DATA_CORRUPTION`, and `TIMEOUT/SLA_FAILURE` do not contribute useful service. A DUE recovered by retry is represented only as `SUCCESS_AFTER_RETRY`; an unrecovered DUE is `DETECTED_FAILURE`. This prevents the invalid shortcut `Q=1-SDC-DUE` unless the event definitions and recovery policy happen to make it exact.
