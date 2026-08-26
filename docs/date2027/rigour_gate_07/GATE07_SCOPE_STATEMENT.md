# Gate 07 frozen paper scope

## Defensible scope

This paper presents a cross-layer evaluation of four correctness- and reliability-qualified 64-bit-payload ECC implementation identities. It shows how categorical correction capability and RTL microarchitecture interact with post-route logic cost, timing feasibility, and activity-based energy under one reproducible SKY130HD flow. Physical conclusions cover three routed implementations; Hsiao remains reliability-only because its frozen physical run stopped at the unchanged synthesis-memory policy.

## What the paper studies

- Conventional combinational and pipelined SECDED `(72,64)` implementations with identical proven W1-correction/W2-detection semantics.
- One generated combinational Hsiao SECDED `(72,64)` implementation for correctness and canonical-coordinate reliability evidence only.
- One shortened BCH `(78,64,t=2)` syndrome/Chien implementation with proven W1/W2 correction.
- Exhaustive W1/W2 guarantees and exhaustive canonical-coordinate W3 SDC/DUE observations, kept semantically separate.
- Standard-cell instance area, cells, routing, timing, post-route OpenSTA power, and timing-feasible steady-stream energy under SKY130HD, TT 1.80 V/25 C, a common 10 ns target, seed 11, and the frozen policy.

## What the paper does not study

It does not solve general ECC selection; establish FIT, SER, operational failure probability, field reliability, physical SRAM-array/interleaving behavior, silicon power, multi-node/PVT robustness, universal ECC-family limits, or a unique best ECC. It does not characterize all possible implementations of SECDED, Hsiao, or BCH.

## Excluded thesis-era components

GREEN Score, carbon analysis, ML selection, NSGA-II, analytical thesis-era energy constants, adaptive scheduling, transition/migration models, SafeForge, and unqualified ECC families are excluded. They provide no manuscript evidence for this paper.
