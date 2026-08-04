# Probability-aware SRAM ECC portfolio co-synthesis

## Scope

The forge supports binary systematic linear block codes with a common `(k,n,r)`
inside a portfolio and hard-decision syndrome decoding. Fault models are finite,
explicit error-vector probability mass functions (PMFs). This is not a universal
ECC construction method and the bundled benchmark PMFs are synthetic rather than
silicon measurements.

For mode `m`, the parity-check and generator matrices are

```text
H_m = [P_m^T | I_r]       G_m = [I_k | P_m]       n = k + r.
```

The independent verifier checks `rank(H_m)=r` and `G_m H_m^T=0`. For each
modeled error vector `e`, it computes `s_m(e)=H_m e^T`, executes the generated
syndrome decoder, and classifies the actual outcome as corrected, detected
uncorrectable (DUE), silent data corruption (SDC), or decoder failure. It does
not infer SDC solely from minimum distance.

## Reliability objectives and constraints

For distribution `q` and code `m`, the reported probability masses are

```text
P_corrected(q,m) = sum p_q(e) over corrected outcomes
P_DUE(q,m)       = sum p_q(e) over detected-uncorrectable outcomes
P_SDC(q,m)       = sum p_q(e) over silent-corruption outcomes
P_residual       = P_DUE + P_SDC + P_decoder_failure.
```

Residual FIT is the distribution's raw FIT multiplied by `P_residual`. SDC and
residual-FIT limits are hard feasibility constraints. Candidate selection is
lexicographic/Pareto-based; there is no implicit weighted sustainability score.

Important correction patterns require nonzero, unique syndromes. Detect-only
patterns require a nonzero syndrome that is absent from the correction map.
Correction maps are explicit artifacts and can intentionally assign additional
syndromes only when the executed-decoder SDC bound remains satisfied.

## Exact and scalable search

The small exact method exhaustively enumerates the configured systematic data
columns, applies rank/weight/syndrome constraints, enumerates feasible decoder
assignments, and reports the complete candidate count, timeout, runtime, and
optimality. It is an equivalent finite Boolean formulation and has no solver
dependency.

The 64-bit method is a seeded deterministic beam search over valid systematic
matrices. It ranks candidates by hard feasibility, corrected PMF mass, structural
hardware proxies, and deterministic tie-breaks. It never certifies itself: the
separate verifier rechecks every emitted matrix over the complete modeled error
universe and performs a seeded campaign beyond that universe.

## Hardware model and shared graph

The structural cost model includes encoder/syndrome XOR count, balanced depth,
fan-in/fan-out, syndrome-table entries, correction-mask ones, mode controls,
configuration bits, output-MUX proxies, and routing proxies. These values are
technology-independent and are not physical area, delay, energy, or leakage.

For each encoder or syndrome output, the shared graph constructs reusable pairwise
XOR expressions and exactly reconstructs every requested linear form. With
received word `y`, this realizes the requested form

```text
z = B y^T
s_m = T_m z XOR R_m y^T
H_m = T_m B XOR R_m.
```

The alternating portfolio search starts from independently valid matrices,
rebuilds the shared graph, proposes matrix changes, independently verifies each
proposal, and retains nondominated reliability/hardware points. The complete
seeded trajectory is recorded. Algebraic reconstruction proves graph/matrix
equivalence; RTL simulation and physical synthesis are additional, tool-dependent
checks.

## Robust deployment boundary

Synthesis, validation, and shifted-test PMFs are separate. A specialized mode is
allowed only inside its validated envelope and while its executed-decoder SDC and
residual-FIT bounds pass. Outside the envelope, the policy uses SECDED only when
SECDED is independently safe for that PMF; otherwise it rejects deployment.

The existing transition-aware scheduler accepts a generated portfolio only after
physical per-access energy, leakage, latency, configuration, migration, and
re-encoding costs are supplied. Structural XOR proxies are insufficient for a
technology-specific break-even or net-benefit claim.

## Evidence levels

- Mathematical certificate: matrix rank, orthogonality, syndrome-map validity,
  decoder-executed PMF outcomes, and shared-graph reconstruction.
- Structural estimate: XOR/depth/table/control/MUX/routing proxies.
- Physical evidence: null unless an identified synthesis/STA/library flow runs.
- Deployment evidence: null until physical mode and transition costs are passed
  through the existing scheduler.

