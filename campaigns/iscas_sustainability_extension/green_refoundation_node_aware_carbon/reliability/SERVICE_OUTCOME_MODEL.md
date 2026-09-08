# Reliability-to-service model

Each requested transaction receives exactly one final outcome:

1. `SUCCESS_NORMAL`: correct payload delivered without correction or retry;
2. `SUCCESS_CORRECTED`: correct payload delivered after an in-ECC correction;
3. `SUCCESS_AFTER_RETRY`: correct payload delivered after one or more retries,
   including a DUE that an external retry successfully recovers;
4. `DETECTED_FAILURE`: useful payload not delivered and failure/DUE detected;
5. `SILENT_DATA_CORRUPTION`: incorrect payload delivered without detection;
6. `TIMEOUT_OR_SLA_FAILURE`: the declared timing policy is violated.

Useful service is the sum of the first three categories only. A correction flag
does not prove correctness: an incorrect delivered payload is SDC unless the
failure is detected. A DUE is not automatically failed service if retry later
delivers the correct payload. If no external SLA is provided, none is invented;
latency remains a Pareto dimension. If an SLA is provided but latency is absent,
the executable model fails closed rather than guessing.

Correction and retry event counts are exported independently for operational
energy. Scrub is a policy event, not a useful transaction; its future reliability
effect and energy must be modeled separately. Retry/scrub energy belongs once in
operational carbon and cannot also be added as recovery/replacement carbon.

Attempt10 logical controls remain exact only over their enumerated mask domains.
They are not physical event probabilities, SER, FIT, or lifetime rates. The
persistent four-step scrub example shows causality: `scrub_on_correct` repairs
the demonstrated single-bit sequence, while a periodic policy can write back a
miscorrection. This is not a calibrated claim that one policy is generally best.
