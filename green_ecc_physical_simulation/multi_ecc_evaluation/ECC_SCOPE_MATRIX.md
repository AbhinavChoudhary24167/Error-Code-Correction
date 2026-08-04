# ECC Scope Matrix

Grouped artifacts are listed once when they share one generator lineage or decoder policy. Registered mathematical identities remain one row each.

| Candidate/artifact group | Status | Code specification | Reason/scope |
|---|---|---|---|
| `extended-hamming-secded-72-64-v1` | `integrated_partially_verified` | `extended-hamming-secded-72-64-v1` | eligible subject to scenario constraints |
| `forge-hotspot-8-4-v1` | `integrated_verified` | `forge-hotspot-8-4-v1` | eligible subject to scenario constraints |
| `forge-spatial-hotspot-72-64-v1` | `integrated_verified` | `forge-spatial-hotspot-72-64-v1` | eligible subject to scenario constraints |
| `forge-sram-portfolio-72-64-v1-geometry-filtered-joint` | `integrated_verified` | `forge-sram-portfolio-72-64-v1-geometry-filtered-joint` | eligible subject to scenario constraints |
| `forge-sram-portfolio-72-64-v1-spatial-hotspot-joint` | `integrated_verified` | `forge-sram-portfolio-72-64-v1-spatial-hotspot-joint` | eligible subject to scenario constraints |
| `hsiao-secded-72-64-v1` | `integrated_verified` | `hsiao-secded-72-64-v1` | eligible subject to scenario constraints |
| `odd-column-secded-4-8` | `integrated_verified` | `odd-column-secded-4-8` | eligible subject to scenario constraints |
| `odd-column-secded-64-72` | `integrated_verified` | `odd-column-secded-64-72` | eligible subject to scenario constraints |
| `primitive-bch-63-51-t2-v1` | `integrated_verified` | `primitive-bch-63-51-t2-v1` | eligible subject to scenario constraints |
| `repository-cyclic-63-51-v1` | `integrated_rejected` | `repository-cyclic-63-51-v1` | excluded |
| `safeforge-robust-72-64-mapping-v1` | `integrated_verified` | `safeforge-robust-72-64-mapping-v1` | eligible subject to scenario constraints |
| `safeforge-robust-8-4-v1` | `integrated_verified` | `safeforge-robust-8-4-v1` | eligible subject to scenario constraints |
| `shortened-bch-71-64-t1-v1` | `integrated_verified` | `shortened-bch-71-64-t1-v1` | eligible subject to scenario constraints |
| `shortened-bch-78-64-t2-v1` | `integrated_verified` | `shortened-bch-78-64-t2-v1` | eligible subject to scenario constraints |
| `shortened-bch-85-64-t3-v1` | `integrated_verified` | `shortened-bch-85-64-t3-v1` | eligible subject to scenario constraints |
| `cpp-bch63-reference` | `duplicate_decoder_policy` | `primitive-bch-63-51-t2-v1` | same primitive polynomial and systematic BCH construction; retained as independent source/test evidence for the registered reference |
| `cpp-secdaec64` | `duplicate_decoder_policy` | `extended-hamming-secded-72-64-v1` | positional extended-Hamming encoder with the same bounded adjacent-pair policy family; no distinct certified codeword set |
| `generated-secded-width-family` | `integrated_experimental` | `—` | complete generated RTL grouped in inventory; lacks archived matrix identity and differential certificate needed for scientific selection |
| `generated-taec-width-family` | `integrated_experimental` | `—` | complete generated RTL but no distinct TAEC matrix certificate; 64b policy is the same collision-prone positional construction |
| `generated-secdaec-64` | `duplicate_decoder_policy` | `extended-hamming-secded-72-64-v1` | same positional extended-Hamming bounded adjacent-pair policy family |
| `generated-bch-labelled-width-family` | `integrated_rejected` | `—` | labelled BCH but uses ad-hoc parity equations, not primitive-field BCH generator construction; decoder equations are not certified against encoder |
| `generated-polar-width-family` | `integrated_experimental` | `—` | transform encoder exists but deployed block is not a deterministic SC/SCL SRAM error-correcting decoder |
| `asic-polar-configurations` | `excluded_insufficient_evidence` | `—` | no correction guarantee and differential deployed-decoder certificate under a declared SRAM error model |
| `polar-python-bound-model` | `excluded_missing_decoder` | `—` | Bhattacharyya/SC block-error bound is a communication-channel analytical proxy, not an executable deployed SRAM decoder |
| `taec-coverage-monte-carlo` | `excluded_missing_mathematical_definition` | `—` | coverage assumptions contain no G/H matrix or executable TAEC encoder/decoder |
| `thesis-taec-75-64-i6-i7` | `excluded_missing_mathematical_definition` | `—` | no (75,64)-I6/I7 matrix, generator, lookup table, RTL, or simulator was found in the repository |
| `repository-hamming-cpp-simulators` | `excluded_insufficient_evidence` | `—` | workload/demo simulators and matrix helpers do not archive a distinct deployed code/decoder identity beyond registered constructions |
| `repetition-external-fixture` | `integrated_verified` | `—` | exhaustive framework extensibility fixture only; explicitly excluded from scientific portfolio |
| `ldpc-reed-solomon-literature-only` | `excluded_missing_encoder` | `—` | no repository encoder, deployed decoder, matrix/polynomial, or framing policy exists |
| `legacy-family-energy-aliases` | `excluded_insufficient_evidence` | `—` | family-level analytical constants and synthetic winners are not bit-exact code/decoder implementations |
