# GREEN-ECC Forge: Certified Probability-Aware SRAM Code Generation and a Negative Study of Joint Hardware Sharing

## Abstract

Existing GREEN-ECC machinery selects and schedules protection modes from a fixed
catalogue. This phase asks a prior question: which short-block systematic matrices
should exist for an explicit SRAM error-vector distribution? We contribute a
reproducible prototype that generates single codes and same-dimension portfolios,
executes each generated syndrome decoder over the modeled universe, enforces hard
silent-data-corruption constraints, emits independent certificates and reference
implementations, and constructs an algebraically verified shared XOR graph.

On one synthetic `(8,4)` PMF, exact synthesis increases corrected mass from 0.48
for equal-redundancy SECDED to 0.91 at zero modeled SDC. A deterministic `(72,64)`
search reaches 0.9839 corrected mass at zero modeled SDC on a synthetic spatial
hotspot PMF. A two-mode portfolio lowers weighted residual probability relative to
one generated general code (0.4008 versus 0.5105). However, joint matrix/hardware
search uses 369 shared XOR proxy gates versus 350 for independently hardware-aware
matrices followed by the same sharing pass. Several shifted distributions also
produce unsafe SDC, and no characterized synthesis flow is available. The evidence
therefore supports an open probability-aware generator and verifier, but not a
positive shared-hardware or deployment-benefit claim.

## Contribution boundary

The precise candidate contribution is the conjunction of explicit SRAM
error-vector PMFs, decoder-executed hard SDC constraints, joint alteration of a
short-block matrix portfolio and a shared encoder/syndrome/correction graph,
independent exhaustive certificates, and distribution-envelope deployment gates.
Automatic FEC synthesis, adaptive ECC, Hamming/Hsiao optimization, fault-class
codes, and XOR common-subexpression elimination are established prior art.

The closest synthesis work is McClurg et al.'s application-specific FEC synthesis,
which already uses SMT/CEGIS and weighted objectives. The distinction tested here
is the SRAM PMF plus actual-decoder SDC constraint plus shared multi-mode graph and
deployment envelope. This repository search is not proof of novelty.

## Method

Each code uses `H=[P^T|I]` and `G=[I|P]`. The independent verifier checks rank,
orthogonality, systematic form, correction-map validity, and actual outcomes. A
dependency-free exhaustive Boolean search proves optimality for small spaces. A
seeded beam search scales the experiment to 64 data bits but makes no optimality
claim. Shared pairwise XOR expressions exactly reconstruct every encoder and
syndrome equation. Alternating search proposes matrix changes under reliability
constraints and records every accepted Pareto move.

## Results and interpretation

The supported positive result is probability-aware code generation under an
equal-redundancy comparison. The small ablation shows that PMF weighting, rather
than the structural hardware tie-break, produces the observed improvement. The
portfolio also outperforms one general generated code on the modeled mixture.

The principal architectural hypothesis is not supported by this experiment. Joint
search trades additional XOR structure for reliability and loses the shared-XOR
comparison against sequential generation. Ordinary synthesis-tool comparison,
equal-area/delay evaluation, equal-reliability physical comparison, and scheduler
break-even analysis remain unavailable. Distribution-shift failures require a
reject-or-certified-fallback policy.

## Reproducibility and limitations

The artifact includes 12 seeded synthetic PMFs, versioned JSON schemas, Python and
C++ reference models, synthesizable SystemVerilog, self-checking testbenches,
matrix/decoder certificates, structural hardware reports, figures, hashes, and
commands. Icarus, Verilator, Yosys/ABC, a Liberty library, silicon PMFs, synthesis,
STA, SPICE, and measured transition costs were unavailable. Consequently physical
PPA, equal-area/equal-delay, carbon, and deployment-net-benefit claims are null.

