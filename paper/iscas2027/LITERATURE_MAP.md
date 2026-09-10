# ISCAS 2027 Literature Map

## Scope and method

This focused map was completed before manuscript drafting. It is not a systematic
review or a priority proof. Sources were selected across ECC construction,
memory-reliability architecture, implementation-aware energy, open physical
design, and semiconductor lifecycle assessment. Bibliographic identities were
checked against DOI records, author-hosted manuscripts, conference records, or
institutional publication pages. The repository source registry controls which
sustainability results may be transferred numerically.

## Prior-work matrix

| Dimension | Primary source | What it establishes | Evidence boundary | Difference from this manuscript |
|---|---|---|---|---|
| Hardware-aware SECDED | M. Y. Hsiao, IBM J. R&D 1970, [DOI](https://doi.org/10.1147/rd.144.0395) | Minimum odd-weight-column SEC-DED construction and hardware-cost motivation | Analytical/historical construction | Hsiao coding is prior art; this work qualifies one named RTL/route identity before comparing it. |
| Low-power memory ECC | S. Ghosh, S. Basu, and N. A. Touba, ITC 2004, [paper](https://users.ece.utexas.edu/~touba/research/itc04-mem.pdf), [DOI](https://doi.org/10.1109/TEST.2004.1387407) | Checker matrix/input ordering can affect switching, area, and delay under memory traces | Synthesized checkers and trace-driven power | Workload dependence is prior art; the present question is whether a preference is admissible after service, full timing, activity, and missing-evidence gates are joined. |
| Cache ECC trade-offs | D. Rossi et al., DATE 2011, [paper](https://eprints.soton.ac.uk/368913/1/date11.pdf), [DOI](https://doi.org/10.1109/DATE.2011.5763257) | Reliability, area, and access-time trade-offs among cache ECC organizations | Architecture/implementation estimates | Establishes multi-objective ECC evaluation, but not this identity-preserving, matched-seed evidence join. |
| Low-delay SEC codes | P. Reviriego et al., IEEE TCAD 2013, [DOI](https://doi.org/10.1109/TCAD.2012.2226585) | Code construction targeted to data-bit protection and decoder delay | Analytical and implementation evaluation | Code optimization is prior art; the present study does not claim a new code. |
| Multi-upset topology | J. A. Clemente et al., IEEE TNS 2021, [DOI](https://doi.org/10.1109/TNS.2021.3099202) | SRAM bitcell topology changes the observed multiple-cell-upset response | Device/layout-aware reliability study | Supports treating bit mapping as required evidence; this repository lacks the exact physical-to-logical map, so no MBU rate is inferred. |
| Physical adjacency and interleaving | M. Wirthlin et al., IEEE TNS 2014, [DOI](https://doi.org/10.1109/TNS.2014.2366913) | A case study identifies physically adjacent MCUs in interleaved, SECDED-protected arrays | Measured/architecture-specific fault mapping | Interleaving benefit is not borrowed: no validated interleaver RTL or topology exists here. |
| Adaptive ECC | Y. S. Lee et al., DATE 2022, [DOI](https://doi.org/10.23919/DATE54114.2022.9774775) | Data-width-aware adaptation trades resilience and cost | DRAM architecture and workload modeling | Adaptivity is established; the present study compares fixed implementations and does not propose a controller. |
| Activity-aware power | F. N. Najm, IEEE TCAD 1993, [DOI](https://doi.org/10.1109/43.205010) | Transition density links workload activity to power estimation | General CAD methodology | Activity annotation itself is not novel; here it is a qualification boundary tied to final routed identity and parasitics. |
| Reproducible RTL-to-GDS | T. Ajayi et al., DAC 2019, [DOI](https://doi.org/10.1145/3316781.3326334) | An inspectable open digital implementation flow | Flow infrastructure | OpenROAD is methodology, not a contribution; the contribution is the controlled evidence admission built on pinned tool identities. |
| Open SRAM generation | M. R. Guthaus et al., ICCAD 2016, [DOI](https://doi.org/10.1145/2966986.2980098) | OpenRAM enables open-source SRAM compilation | Compiler/tool paper | The local 256x72 attempt did not finish DRC/LVS/characterization; no successful OpenRAM result is claimed. |
| Architectural carbon | U. Gupta et al., ISCA 2022, [DOI](https://doi.org/10.1145/3470496.3527408) | Embodied and operational carbon can be modeled jointly at architectural scale | Coefficient-based lifecycle model | Supplies equation structure only; its coefficients are not relabeled as SKY130 measurements. |
| Fab LCA trends | M. Garcia Bardon et al., IEDM 2020, [DOI](https://doi.org/10.1109/IEDM13553.2020.9372004) | PPAC-E and bottom-up process-flow sustainability analysis | Advanced-node historical/modelled trends | Used only for methodological alignment and trend context, never SKY130 calibration. |
| Cradle-to-gate logic LCA | L. Boakes et al., IEDM 2023, [DOI](https://doi.org/10.1109/IEDM45741.2023.10413725) | Explicit cradle-to-fab-gate scope, yield, electricity, and process assumptions | Generic high-volume advanced-node model | Demonstrates boundary discipline; the node/process/system boundary does not match the local SKY130 experiment. |
| IC-production review | T. Pirson et al., IEEE TSM 2023, [DOI](https://doi.org/10.1109/TSM.2022.3228311) | Historical IC footprint studies use heterogeneous scopes and normalizations | Review of 27 sources | Motivates refusal to merge incompatible coefficients. |
| Embodied-carbon uncertainty | X. Chen et al., ICCAD 2025, [DOI](https://doi.org/10.1109/ICCAD66269.2025.11240799) | Yield, fab carbon intensity, and process inputs create distributions rather than single constants | Model-based uncertainty analysis | Supports symbolic/scenario reporting; published distributions do not fill the missing SKY130 inventory. |

## Defensible gap

The literature establishes hardware-conscious ECC matrices, workload-sensitive
checker energy, reliability/area/performance evaluation, adaptive protection,
activity-aware CAD, reproducible physical design, and lifecycle-carbon modeling.
Within this focused set, the unresolved methodological question is narrower:
**which SRAM-protection preferences remain identifiable when categorical service,
one implementation identity, setup and hold feasibility, post-route operation
energy, and lifecycle boundaries are admitted together without imputing blocked
quantities?** This is an audit observation, not a claim of publication priority.

## Novelty language admitted

- An evidence-qualified decision procedure, not a new ECC code or power method.
- A matched experiment in which infeasibility and missingness remain results,
  rather than being silently repaired or mixed into a Pareto set.
- Measured-coefficient workload and symbolic lifecycle break-even boundaries,
  without a global-winner claim.

## Novelty language rejected

- “First,” “unique,” “optimal,” “state of the art,” or “globally greenest.”
- Novelty based on Hsiao construction, activity-aware power, or open-source P&R.
- Numerical SKY130 lifecycle carbon from advanced-node or architecture literature.
- Physical multi-bit-upset rates without a physical-to-logical bit map and event model.
