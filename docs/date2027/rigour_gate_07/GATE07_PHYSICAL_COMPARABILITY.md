# Gate 07 physical-comparability audit

## Common controls

| Control | Frozen value |
|---|---|
| Container | `openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e` |
| ORFS / OpenROAD | `56496f3980fb6e9e58f10c8aea4a98949c0fe5f2` / `ab6fd26351dc449e69059684dc6aa9ae9046eb36` |
| Platform / corner | SKY130HD / TT 1.80 V, 25 C |
| Target / I/O delays | 10.0 ns / 10% input and 10% output |
| Output load | 0.05 pF |
| Core utilization policy / placement density | 35% / 0.55 |
| Seed / workers | 11 / 1 |
| Useful payload / II | 64 bits / 1 cycle |
| Area metric | final standard-cell instance area, never nominal die/core area |

All routed implementations use the same technology, corner, physical policy, constraint methodology, load, density, seed, and worker count. Achieved Fmax is `1000 / (10 ns - worst setup slack)` MHz; negative slack is retained. The comparison boundary exercises independent encoder and decoder channels in parallel for each accepted transaction.

## Legitimate architectural differences and exceptions

- Nominal latency is 1 cycle for combinational SECDED and BCH, and 3 cycles for pipelined SECDED. This is retained rather than normalized away.
- SECDED uses a 72-bit protected word; BCH uses 78 bits for the same 64-bit payload. The extra six protected bits are a real part of the evaluated BCH cost, but prevent attributing all cost solely to decoder algebra.
- Hsiao PPA is unavailable. Its decoder inferred a 256×73 table, exceeding the unchanged ORFS `SYNTH_MEMORY_MAX_BITS=4096` policy. The policy was not relaxed post hoc; Hsiao is excluded from PPA conclusions.
- BCH completes routing with zero final DRC but fails the common target. Its target-constraint power is diagnostic and its target-clock energy is not an achievable operating point.
- Power values are post-route OpenSTA estimates, not silicon measurements.

Hsiao omission reviewer risk: `MEDIUM`. The cause and non-relaxation are traceable, but the missing point reduces physical breadth.
