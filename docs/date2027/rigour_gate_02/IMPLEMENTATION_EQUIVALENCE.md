# Implementation Equivalence

Gate 02 distinguishes mathematical identity from executable-path equivalence. Adjacency below is logical storage-coordinate adjacency, never physical adjacency.

The registered Python BCH reference uses a bounded exact syndrome locator. `src/bch63.*` is an existing independent C++ path using its own primitive-field construction, Berlekamp–Massey locator and Chien search. A thin driver may expose it; no Python algorithm is translated into C++.

The independent C++ comparison passed 54 encoding probes and all 2,017 masks through `t=2`, including decoding and native flags. All five registered RTL sources compiled in the single bounded Icarus attempt. Cyclic and TAEC execution timed out at 120 seconds; Hsiao, SECDED and SEC-DAEC `vvp` processes exited with host access violation `3221225477` and emitted no scientific comparison output. Complete RTL differential evidence is therefore `NOT ASSESSABLE`, not failed and not inferred passing.

`SecDaec64.hpp` declares 73 total bits as written. It is unregistered and is not treated as an independent `(72,64)` implementation.

| Implementation | Canonical mapping | Executable paths | Gate-02 status |
|---|---|---|---|
| `cyclic-rtl-bounded-search-63-51-v1` | canonical-data-low-to-polynomial-parity-low | Python reference; registered RTL path requires the recorded Icarus differential result | REJECTED |
| `forge-hotspot-8-4-v1-archived-table-decoder` | canonical-direct | Python reference | PASS |
| `forge-spatial-hotspot-72-64-v1-archived-table-decoder` | canonical-direct | Python reference | PASS |
| `forge-sram-portfolio-72-64-v1-geometry-filtered-joint-archived-table-decoder` | canonical-direct | Python reference | PASS |
| `forge-sram-portfolio-72-64-v1-spatial-hotspot-joint-archived-table-decoder` | canonical-direct | Python reference | PASS |
| `hsiao-generated-combinational-72-64-v1` | canonical-direct | Python reference; registered RTL path requires the recorded Icarus differential result | CONDITIONAL PASS |
| `odd-column-secded-4-8-archived-table-decoder` | canonical-direct | Python reference | PASS |
| `odd-column-secded-64-72-archived-table-decoder` | canonical-direct | Python reference | PASS |
| `primitive-bch-63-51-t2-v1-reference-decoder` | canonical-data-low-to-polynomial-parity-low | Python reference; existing independent C++ BCH63 path | PASS |
| `safeforge-robust-72-64-mapping-v1-archived-table-decoder` | canonical-direct | Python reference | PASS |
| `safeforge-robust-8-4-v1-archived-table-decoder` | canonical-direct | Python reference | PASS |
| `secdaec-rtl-bounded-72-64-v1` | canonical-to-positional-RTL | Python reference; registered RTL path requires the recorded Icarus differential result | REJECTED |
| `secded-rtl-combinational-72-64-v1` | canonical-to-positional-RTL | Python reference; registered RTL path requires the recorded Icarus differential result | CONDITIONAL PASS |
| `shortened-bch-71-64-t1-v1-reference-decoder` | canonical-data-low-to-polynomial-parity-low | Python reference | PASS |
| `shortened-bch-78-64-t2-v1-reference-decoder` | canonical-data-low-to-polynomial-parity-low | Python reference | PASS |
| `shortened-bch-85-64-t3-v1-reference-decoder` | canonical-data-low-to-polynomial-parity-low | Python reference | PASS |
| `taec-rtl-bounded-72-64-v1` | canonical-to-positional-RTL | Python reference; registered RTL path requires the recorded Icarus differential result | PARTIAL |

Generated-width families without a registered independent generator/specification and executable differential path are `NOT ASSESSABLE`; SafeForge generation was not modified.
Wrappers (`sec_ded_64`, `sec_daec_64`, `taec_64`, `bch_63`), aliases and duplicated source paths do not increase the 17 registered implementation count.
