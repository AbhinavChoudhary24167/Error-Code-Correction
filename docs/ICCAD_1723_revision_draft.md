# GREEN-ECC: An Architecture-Aware and Uncertainty-Aware Framework for Lifecycle-Constrained Memory ECC Selection

> Manuscript-ready revision text. The original paper/thesis source and
> bibliography are absent from this checkout, so this Markdown file cannot
> preserve its page layout, figure numbers, cross-references, or citations.
> Integrate this text into the authoritative source before submission.

## 1. Introduction and contributions

Memory error protection is not free, and making protection selectable is not
free either. A recommendation based only on decoder-level reliability or a
software ranking can reverse once storage padding, encoder/decoder selection,
protected mode state, inactive engines, and data migration are included.
GREEN-ECC therefore treats each recommendation as conditional on a candidate
set, workload, fault model, technology/PVT provider, lifecycle assumptions,
constraints, and uncertainty bounds; it does not claim universal optimality.

The revised contributions are:

1. An extensible, architecture-aware distinction among design-time fixed,
   boot-time/bank-configurable, and runtime-adaptive ECC.
2. Exact logical MUX and fixed-container accounting, protected metadata, a
   selection-hardware fault tree, and safe reconfiguration semantics.
3. Explicit operational and embodied-carbon interfaces with unit-checked
   conversion and machine-readable provenance.
4. Transparent hard-constraint filtering, exact Pareto enumeration for small
   spaces, declared preference selection, baseline regret, score diagnostics,
   and fixed-seed robustness analysis.
5. Executable JSON, register-map, and SystemVerilog policy outputs plus an RTL
   reference MUX/controller.

Pareto analysis and NSGA-II are established methods, not novelty claims.

## 2. Background and related work

A single-bit upset/error (SBU/SBE) changes one stored bit. A double-bit
upset/error (DBU/DBE) changes two bits, while a multi-bit upset (MBU) affects
multiple bits, often with spatial adjacency. Single-error correction,
double-error detection (SECDED) corrects one error and detects two.
Single-error correction, double-adjacent-error correction (SEC-DAEC) adds a
declared adjacent-pair capability; triple-adjacent-error correction (TAEC)
targets adjacent triples. Bose-Chaudhuri-Hocquenghem (BCH) codes are
parameterized algebraic block codes. Successive-cancellation (SC) is the
decoder assumed for the short Polar configuration in the present ablation.

Hazucha and Svensson's atmospheric-neutron soft-error model motivates the
legacy critical-charge-based analytical path, but the repository's example
Qcrit record is not a verified reproduction of their experiment [1]. Das and
Touba describe burst-correcting codes for SRAM MBUs, and CLEAR distinguishes
spatial MBUs, interleaving, adjacent-error codes, and temporal accumulation
[2,3]. These works motivate explicit fault-distribution and adjacency inputs
instead of mapping one severity label to a universal hardware conclusion.

Adaptive protection already has architectural precedent. CREAM varies DRAM
protection to trade capacity and reliability, while Memory Mapped ECC changes
where correction information is stored to reduce SRAM cost [4,5]. Their
architectural accounting motivates GREEN-ECC's separation between selecting a
code offline and implementing a selectable datapath.

NSGA-II is a standard elitist multi-objective evolutionary algorithm [6]. For
the small discrete set evaluated here, exact enumeration is simpler and
auditable; evolutionary search is retained only as a future option for a truly
combinatorial space. The declared preference stage is closer to
multi-attribute utility analysis, whose validity depends on explicit
preference-independence assumptions, than to an objective universal score [7].

Lifecycle-carbon research distinguishes operational emissions from hardware
manufacturing and infrastructure. Chasing Carbon and ACT show why architects
must expose embodied assumptions and why a carbon-optimal architecture can
differ from a performance/efficiency optimum [8,9]. GREEN-ECC adopts that
accounting separation but does not reuse their numerical factors without a
sourced dataset.

Polar codes originate from channel polarization and have asymptotic guarantees
with `O(N log N)` encoding/decoding constructions [10]. Those guarantees do not
establish that a short `(64,48)` SC implementation is competitive for an SRAM
word. The Polar result here is accordingly an ablation of a projected model,
not a general conclusion about the family.

## 3. Architecture

Design-time selection instantiates only the chosen encoder/decoder and has zero
selection-MUX, mode-metadata, and migration overhead. Boot-time or bank-level
configuration instantiates multiple gated/parallel engines or a shared
datapath, a protected mode register, routing and MUXes, and a safe fallback.
Runtime adaptation additionally changes mode by page/bank/epoch and therefore
requires quiescence, decode-under-old-mode, re-encode/write-under-new-mode,
verification, atomic metadata commit, and capacity for in-flight migration.

The revision uses a fixed `n_max` physical slot. Candidate `i` consumes
`ceil(k_logical/k_i)n_i` bits; all remaining positions are explicit padding.
For a pruned balanced tree, `d_mux=ceil(log2 M)` and
`N_2:1(b,M)=b(M-1)`. A complete tree uses
`b(2^ceil(log2 M)-1)`. The total is summed over codeword, decoded-data, and
status paths (plus shared input routing when applicable). The five-mode example
uses a 128-bit container, 64-bit data, and four-bit status, giving 784 2:1 MUX
cells and depth three for parallel/gated-parallel output selection. A shared
input route raises the logical count to 1,296. The fixed case remains zero.

The controller RTL applies a safe reset/fallback, rejects illegal modes,
defers a requested change until the datapath is safe, and triplicates mode
metadata. These are functional reference semantics, not a synthesized PPA
claim.

## 4. Reliability, PPA, and lifecycle carbon

Latency is never a single ambiguous number. We distinguish codec latency,
memory-path latency, MUX/routing latency, controller/metadata latency, and
end-to-end read/write latency. Energy is separated into selected-engine
dynamic energy, inactive/glitch energy, leakage, scrub, selector/metadata, and
migration. Carbon overhead means incremental operational plus embodied CO2e
attributable to ECC/adaptability, reported separately from absolute system
carbon.

For characterized 2:1 cells, the model uses
`A_mux=sum(N_p A_2:1)+A_route`,
`t_mux,p=d_p t_2:1(V,T,node)+t_wire,p`,
`E_mux,p=sum(alpha_g C_g V^2)`, and
`P_leak=sum(V I_leak,g)`. `alpha` is transitions per cell per operation; no
extra one-half factor is used. Exact node/VDD/temperature/corner matching is
required and synthesis outranks analytical counts at the same PVT.

The fault-tree approximation is
`1-(1-P_ECC)(1-P_mux)(1-P_controller)(1-P_metadata)`. It assumes independent
events and omits unavailable terms rather than treating them as zero. Runtime
migration energy is
`N_migrated(E_read/decode,old+E_encode/write,new)+E_control`; the current
legacy record can only supply a labeled per-access proxy.

Operational carbon is
`CI[kgCO2e/kWh] E_lifetime[J]/3.6e6`. Embodied inputs expose area,
manufacturing intensity, yield, die allocation, package allocation, lifetime
accesses, amortization, and source. No sourced manufacturing or selectable-cell
data is present, so new adaptive physical PPA and incremental lifecycle carbon
are unavailable rather than fabricated.

## 5. Problem formulation and selection

The primary process first rejects violations of maximum FIT, latency, energy,
area, carbon, minimum capacity efficiency, and policy constraints. It then
enumerates the exact non-dominated set across fully characterized objectives
and selects using declared non-negative normalized preference costs. It reports
the runner-up and regret relative to the lowest feasible preference cost.

ESII (Environmental Sustainability Improvement Index) is a bounded product of
log-risk-reduction utility and a weighted energy/carbon burden utility. Its
range is `[0,1]`, with larger better. NESII (Normalized ESII) is a winsorized
min-max mapping of an ESII reference set to `[0,100]`; with fixed bounds it is
monotone in ESII and therefore cannot independently validate an ESII winner.
GREEN Score (GS) is a separate bounded reliability/carbon/latency utility.
Tests cover zero-safe transforms, monotonicity, a synthetic GS disagreement,
rank correlations, and the sufficient coincidence condition: a candidate that
component-wise dominates every alternative must win under every strictly
monotone utility with matching directions.

## 6. Experimental methodology

The repository does not contain the generator or factorization of the claimed
original 189 scenarios, so that number is not reconstructed. The reproducible
revision configuration contains three operating scenarios, five ECC families,
five concrete configurations, and fifteen candidate-scenario evaluations.
These counts are reported separately.

The example evaluates node 16 nm, 0.8 V, 75 degrees C as requested scenario
coordinates. They are not physical-validation evidence. Reliability is the
legacy analytical/calibrated path. Candidate codec area and latency are legacy
projections. Adaptive MUX/controller physical metrics and incremental embodied
carbon are unavailable. Monte Carlo uses 300 samples, seed 1723, and independent
uniform multiplicative intervals of 20% FIT, 15% energy, 20% carbon, and 10%
latency. This is a stress test, not a fitted probability model.

Reproduce all revision artifacts with:

```bash
python3 scripts/run_revision_study.py
```

The result manifest records the input hash, repository commit, metric-source
classes, output hashes, and reproduction command. Exact Pareto complexity is
`O(S*C^2)` time and `O(S*C)` stored results; a synthetic host-dependent scaling
benchmark is generated separately.

## 7. Results, baselines, scalability, robustness, and ablations

The baselines are static SECDED, strongest feasible reliability, minimum
feasible energy, minimum feasible carbon, fault-regime lookup, exact Pareto plus
preference, and the current GREEN-ECC policy. When physical objectives are
unavailable, energy/carbon baselines explicitly fall back and the Pareto set is
reduced to characterized objectives.

In the shipped revision study, GREEN-ECC differs from the simple lookup in all
three scenarios: moderate cases select BCH instead of SEC-DAEC and the heavy
case selects TAEC instead of BCH. Because FIT is the only complete architecture
objective, these are reliability-driven differences, not evidence of a carbon,
MUX-PPA, or migration advantage. No favorable counterfactual is manufactured.

The Polar `(64,48)` SC projection has zero Pareto memberships. The generated
ablation records its rate, projected FIT/carbon/latency, and every candidate
that dominates it on the legacy objectives. Likely causes include a short block,
SC latency assumptions, and an analytical coverage mapping that is not tied to
a measured SRAM channel. Polar remains an educational ablation and should not
support a family-wide claim.

**Interpretation for revised Figure 4 (topology MUX comparison).** Fixed ECC
has zero selector cells, parallel and gated-parallel share 784 logical 2:1 MUX
cells, and the shared/reconfigurable model reaches 1,296 because it adds a
128-bit input-routing path. This matters because “adaptive ECC” is not a free
software choice: even before physical characterization, selection structure
and storage format differ materially by deployment topology.

Place the generated vector Figure 4 immediately after this paragraph and before
the references. Do not use the blank physical-PPA panel as evidence.

## 8. Limitations and threats to validity

The dominant limitation is missing characterization: no Liberty, synthesis,
STA, SPICE, or measured MUX/controller artifact is available. Candidate PPA and
embodied defaults are projected, the Qcrit example provenance is unverified,
fault-tree independence is approximate, and uncertainty intervals are elicited
rather than statistically fitted. The candidate set is small. Polar is not
fairly hardware-calibrated. The manuscript source is absent, so page-limit,
reference-resolution, figure-placement, and typesetting checks remain blocked.

## 9. Conclusion

The revision changes GREEN-ECC from a textual recommendation path into an
extensible architecture-aware DSE and deployment framework. Its strongest
current evidence is exact logical overhead, explicit assumptions/provenance,
transparent exact selection and baselines, reproducible uncertainty analysis,
and executable policy artifacts. Physical and lifecycle conclusions remain
conditional on future characterized providers.

## Verified primary references

1. P. Hazucha and C. Svensson, “Impact of CMOS technology scaling on the atmospheric neutron soft error rate,” *IEEE TNS* 47(6), 2586-2594, 2000. DOI: https://doi.org/10.1109/23.903813
2. A. Das and N. A. Touba, “Low Complexity Burst Error Correcting Codes to Correct MBUs in SRAMs,” GLSVLSI 2018. DOI: https://doi.org/10.1145/3194554.3194570
3. H. Farbeh and A. M. Hosseini Monazzah, “CLEAR: Cache Lines Error Accumulation Reduction by exploiting invisible accesses,” *Microelectronics Journal* 90, 123-132, 2019. DOI: https://doi.org/10.1016/j.mejo.2019.05.020
4. Y. Luo et al., “Using ECC DRAM to Adaptively Increase Memory Capacity,” arXiv:1706.08870, 2017. https://arxiv.org/abs/1706.08870
5. D. H. Yoon and M. Erez, “Memory mapped ECC: low-cost error protection for last level caches,” ISCA 2009. DOI: https://doi.org/10.1145/1555754.1555771
6. K. Deb, A. Pratap, S. Agarwal, and T. Meyarivan, “A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II,” *IEEE TEC* 6(2), 182-197, 2002. DOI: https://doi.org/10.1109/4235.996017
7. R. L. Keeney, “Utility Functions for Multiattributed Consequences,” *Management Science* 18(5), 276-287, 1972. DOI: https://doi.org/10.1287/mnsc.18.5.276
8. U. Gupta et al., “Chasing Carbon: The Elusive Environmental Footprint of Computing,” HPCA 2021. DOI: https://doi.org/10.1109/HPCA51647.2021.00076
9. U. Gupta et al., “ACT: Designing Sustainable Computer Systems With An Architectural Carbon Modeling Tool,” ISCA 2022, 784-799. DOI: https://doi.org/10.1145/3470496.3527408
10. E. Arikan, “Channel Polarization: A Method for Constructing Capacity-Achieving Codes for Symmetric Binary-Input Memoryless Channels,” *IEEE TIT* 55(7), 3051-3073, 2009. DOI: https://doi.org/10.1109/TIT.2009.2021379
