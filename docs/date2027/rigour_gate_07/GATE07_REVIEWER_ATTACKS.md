# Gate 07 hostile-review audit

Classification describes the potential severity before the frozen resolution. `RESOLVED_FOR_SCOPE` means the claim/table/figure wording now survives without adding measurements; it does not mean the missing experiment exists.

## Reviewer A — Dependability / ECC

| ID | Classification | Attack | Resolution | Needs new experiment? | State |
|---|---|---|---|---|---|
| A1 | CRITICAL | Weight-3 SDC/DUE could be misread as operational reliability or a correction guarantee. | Use “exhaustive canonical-coordinate observations” everywhere; keep guarantee and observation columns separate. | Yes, for field rates—not for frozen claims. | RESOLVED_FOR_SCOPE |
| A2 | MAJOR | No FIT/SER or field-weighted fault distribution exists. | Remove all such claims and state the limitation in Setup and Discussion. | Yes. | RESOLVED_FOR_SCOPE |
| A3 | MAJOR | Comparing W3 fractions across 72- and 78-bit codes can imply a common operational distribution. | Report raw denominators and codeword widths; prohibit cross-code field interpretation. | Yes, for operational comparison. | RESOLVED_FOR_SCOPE |
| A4 | MAJOR | Hsiao appears selectively omitted from PPA. | State the preserved 256×73-table / 4096-bit frozen-policy failure and retain Hsiao in reliability evidence. | Yes, for Hsiao PPA. | RESOLVED_FOR_SCOPE |
| A5 | MINOR | Pipelined SECDED inherits reliability evidence rather than rerunning every mask on the timed boundary. | Cite exact Gate 03R temporal-alignment equivalence and preserve the implementation identity transfer. | No. | RESOLVED_FOR_SCOPE |

## Reviewer B — EDA / physical design

| ID | Classification | Attack | Resolution | Needs new experiment? | State |
|---|---|---|---|---|---|
| B1 | MAJOR | Area and timing may be incomparable if constraints or floorplanning differ. | Freeze the common image, ORFS/OpenROAD, SKY130HD corner, SDC, load, density, utilization policy, seed, and worker count; use instance area, not die area. | No. | RESOLVED_FOR_SCOPE |
| B2 | MAJOR | “Achieved Fmax” may hide target-period slack semantics. | Define it as `1000/(10 ns - worst setup slack)` and retain WNS/timing deficit. | No. | RESOLVED_FOR_SCOPE |
| B3 | CRITICAL | The 24.016% energy result could be caused by an incomplete pipeline drain, different work, or trace length. | Audit the shared 100,000-operation VCD, six reset cycles, four drain cycles, II=1, latency 1/3, identical duration, annotation, and energy formula. | No. | RESOLVED_FOR_SCOPE |
| B4 | MAJOR | OpenSTA power is not measured silicon power. | Call it post-route activity-based estimation and avoid absolute silicon-efficiency claims. | Yes, for silicon claims. | RESOLVED_FOR_SCOPE |
| B5 | MAJOR | BCH’s 78-bit codeword versus SECDED’s 72-bit codeword biases cost. | State same 64-bit useful payload but different protected widths; redundancy is part of the evaluated implementation cost. | No. | RESOLVED_FOR_SCOPE |
| B6 | MAJOR | A common target disadvantages a long combinational BCH datapath. | Treat target failure as scoped data, never a family limit; do not interpret target-clock energy as achievable. | Yes, for timing-normalized energy. | RESOLVED_FOR_SCOPE |
| B7 | MINOR | One seed cannot establish physical variability. | Limit reproducibility to the qualified deterministic seed policy and report no process/seed distribution. | Yes, for variability. | RESOLVED_FOR_SCOPE |

## Reviewer C — DATE novelty / program committee

| ID | Classification | Attack | Resolution | Needs new experiment? | State |
|---|---|---|---|---|---|
| C1 | CRITICAL | Repository-local notes do not establish any “first” or universal novelty claim. | Remove priority language; frame a scoped contribution and require conventional related-work positioning during writing. | No scientific measurement; broader literature audit remains. | RESOLVED_FOR_SCOPE |
| C2 | MAJOR | Four reliability identities and three routed points may look like an engineering report. | Center the paper on identity qualification, the controlled same-semantics microarchitecture experiment, and the correction-versus-feasibility contrast. | More points would strengthen breadth but are not required for these claims. | RESOLVED_FOR_SCOPE |
| C3 | MAJOR | Missing Hsiao PPA weakens the code-level comparison. | Make missingness a visible frozen-policy result and exclude Hsiao from every physical claim. | Yes, for a complete Hsiao PPA comparison. | RESOLVED_FOR_SCOPE |
| C4 | MAJOR | “Pipelining trades area for speed” is qualitatively obvious. | Claim the measured, reproducible effect sizes and energy/latency distinction—not the generic intuition—as the empirical result. | No. | RESOLVED_FOR_SCOPE |
| C5 | MAJOR | The framework could be indistinguishable from an internal characterization harness. | Present its fail-closed identity, provenance, missing-data, and cross-layer semantic controls as methodological support; do not claim tooling alone as novelty. | No. | RESOLVED_FOR_SCOPE |
| C6 | MAJOR | Local literature notes target different thesis subsystems and do not close external novelty. | Freeze only three non-priority contributions and carry external positioning as a high reviewer risk, not an unsupported claim. | No new experiment. | RESOLVED_FOR_SCOPE |
| C7 | MINOR | Four figures plus large tables exceed a six-page budget and repeat information. | Keep three figures, drop the reliability plot, and freeze two major tables. | No. | RESOLVED_FOR_SCOPE |

No unresolved `CRITICAL` issue remains after claim removal/narrowing and the energy audit.
