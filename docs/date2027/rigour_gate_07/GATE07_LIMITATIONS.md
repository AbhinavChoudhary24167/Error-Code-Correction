# Gate 07 reviewer-safe limitations freeze

## Experimental Setup

- SKY130HD only, at TT 1.80 V / 25 C; no node, library, voltage, temperature, or process-corner generalization.
- Specific evaluated RTL implementations only; these do not exhaust SECDED, Hsiao, or BCH architectures.
- One common primary 10 ns constraint, one qualified deterministic seed policy, and one worker; no seed/process distribution is claimed.
- SECDED and BCH protect the same 64-bit payload but use 72- and 78-bit codewords, respectively.
- Power is a post-route OpenSTA activity estimate, not a silicon measurement.

## Results

- Hsiao PPA is unavailable because its inferred 256×73 table exceeded the unchanged 4096-bit ORFS synthesis-memory policy; it is excluded from physical conclusions.
- BCH misses the 10 ns target. Its target-constraint power is diagnostic and its energy is not interpreted as achievable 100 MHz operating energy.
- The energy comparison is a steady-stream II=1 result; pipelined SECDED has two additional cycles of request latency.

## Discussion

- No FIT, SER, operational field-error probability, or physically weighted SDC/DUE model is established.
- Weight-3 SDC/DUE values are exhaustive canonical-coordinate observations, not operational probabilities or correction guarantees.
- No final physical SRAM array, bit mapping, interleaving, scrub policy, or memory-macro cost is characterized.
- Only four reliability identities, three routed designs, and two timing-feasible energy points are available.
- External novelty is not established by the repository-local notes; the manuscript must avoid priority claims and position the contribution conventionally.

## Artifact-only detail

Full-precision error-class power differences, native JSON serialization precision, raw transition counts, and infrastructure-attempt inventories remain available in the frozen artifacts but do not belong in the six-page main text unless needed to answer review.
