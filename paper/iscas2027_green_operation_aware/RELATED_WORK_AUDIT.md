# Focused related-work and novelty audit

## Audit boundary

This is a focused audit for claim control, not a systematic review or a priority proof. Sources were selected across the technical dimensions named in the paper brief and checked against primary papers, author-hosted manuscripts, conference proceedings, or institutional publication records. The audit was performed on 2026-09-09.

## Technical-dimension matrix

| Dimension | Representative primary work | Abstraction and metrics | Activity model | Physical evidence | Reliability evidence | Sustainability | Consequence for this paper |
|---|---|---|---|---|---|---|---|
| Hsiao construction | Hsiao, 1970, [DOI](https://doi.org/10.1147/rd.144.0395), [author-hosted copy](https://people.eecs.berkeley.edu/~kubitron/cs252/handouts/papers/hsiao70.pdf) | Code construction; parity-matrix weight, cost, performance | none | historical implementation reasoning, not this flow | coding-theoretic SECDED | none | Hsiao coding and sparse odd-weight columns are established, not contributions here. |
| Low-power memory ECC checkers | Ghosh, Basu, and Touba, 2004, [author-hosted paper](https://users.ece.utexas.edu/~touba/research/itc04-mem.pdf), [DOI](https://doi.org/10.1109/TEST.2004.1387407) | ECC checker power/area/delay and parity-matrix/input-order optimization | application memory traces from SPEC and MediaBench | synthesized checker experiments; not a matched multi-seed post-route SRAM-wrapper study | SECDED semantics | none | Workload-dependent ECC switching and Hamming/Hsiao power optimization are prior art. |
| SRAM/cache ECC architecture evaluation | Rossi et al., 2011, [author manuscript](https://eprints.soton.ac.uk/368913/1/date11.pdf), [DOI](https://doi.org/10.1109/DATE.2011.5763257) | Cache organization, area, access time, correction capability | not an operation-separated routed VCD study | implementation estimates for cache organizations | SECDED/DEC correction analysis | none | Reliability–area–performance tradeoffs are established; “finding the best ECC” is not a defensible gap. |
| Low-delay ECC implementation | Reviriego et al., 2013, [DOI](https://doi.org/10.1109/TCAD.2012.2226585) | SEC/SECDED construction; encoder/decoder delay and area | none | ASIC-oriented implementation evaluation | coding capability | none | Code/checker hardware optimization is established. |
| Synthesized SECDED/DAEC comparison | Tripathi et al., 2020, [arXiv](https://arxiv.org/abs/2002.07507) | ASIC synthesis; area, power, delay | synthesis power assumptions | synthesis, not matched post-route parasitic-aware E5 | functional code design | none | Synthesis-level Hamming/Hsiao comparisons are not new; this paper must identify its post-route activity boundary. |
| Activity-aware power estimation | Najm, 1993, [DOI](https://doi.org/10.1109/43.205010); Najm, 1994, [author-hosted survey](https://www.eecg.utoronto.ca/~najm/papers/tvlsi94-survey.pdf) | switching activity and VLSI power estimation | probabilistic and simulation-derived activity | general CAD methodology | none | none | Dependence of power estimates on input activity is established. The contribution is the matched ECC result, not activity annotation itself. |
| Open physical-design flow | Ajayi et al., 2019, [OpenROAD publications](https://theopenroadproject.org/publications/), [author-hosted paper](https://www.ece.umn.edu/users/sachin/conf/dac19-OR.pdf) | RTL-to-GDSII open flow, STA, extraction | flow-dependent | full digital implementation toolchain | none | none | OpenROAD use supports reproducibility but is not a novelty claim. |
| Cross-layer reliability/energy design | Pajouhi, Fong, and Roy, 2015, [DATE paper](https://past.date-conference.com/proceedings-archive/2015/pdf/0145.pdf) | device/circuit/architecture co-design; yield, cell area, power | model-driven | 32 nm STT-MRAM design study | model-derived yield | none | Cross-layer reliability/energy optimization is established and differs from the present evidence-qualification focus. |
| Workload/adaptive ECC | Wei et al., 2020, [DATE paper](https://www.date-conference.com/proceedings-archive/2020/pdf/0364.pdf); Lee et al., 2022, [author page](https://csarch.korea.ac.kr/publication/dram_ecc_date22/) | GPGPU register-file and DRAM architecture; energy/performance/reliability | application/value-dependent | architecture/simulation studies | model/simulation-derived failure behavior | none | Workload- or data-dependent ECC selection is established. GREEN’s contribution is not adaptivity. |
| Semiconductor sustainability | Garcia Bardon et al., 2020, [imec record](https://imec-publications.be/entities/publication/6791c88e-2b5b-406a-a3ea-6de1b8122335), [DOI](https://doi.org/10.1109/IEDM13553.2020.9372004); imec SSTS [white paper](https://www.imec-int.com/sites/default/files/2022-07/Whitepaper_SSTS_FINAL.pdf) | bottom-up manufacturing/LCA and PPAC-E | process and use assumptions | process-model data, not this repository | none | manufacturing and lifecycle methodology | Methodological alignment is supportable; imec certification, SKY130 embodied carbon, and absolute lifecycle claims are not. |

## Gap statement retained

The checked literature establishes Hsiao construction, ECC power optimization under traces, synthesis/architecture tradeoffs, activity-dependent power estimation, cross-layer optimization, adaptive ECC, and semiconductor LCA methods. Within this focused set, we did not identify a study that asks whether a five-seed vectorless Hamming/Hsiao ordering survives operation-separated, final-routed activity with extracted parasitics while explicitly excluding uncharacterized macro-internal energy. This is an audit observation, not a “first” claim.

The defensible novelty language is therefore: **a matched, evidence-qualified empirical test of ordering preservation across activity models, coupled to a transparent workload boundary.** The paper avoids “first,” “unique,” “optimal,” and “state of the art.”

## Rejected candidate novelty claims

- `REJECTED`: Hsiao coding or minimum odd-weight-column construction is new.
- `REJECTED`: using workload activity to reduce ECC power is new.
- `REJECTED`: activity-aware post-route power estimation is new.
- `REJECTED`: cross-layer reliability/energy optimization or Pareto comparison is new.
- `REJECTED`: GREEN establishes an optimal ECC or a global winner.
- `REJECTED`: the work establishes absolute semiconductor or SKY130 lifecycle carbon.
- `REJECTED`: the checked literature proves publication priority for the exact experiment. A broader systematic search would be required for a priority claim, so no such claim appears.

## ISCAS 2027 format check

The [official call](https://2027.ieee-iscas.org/call-for-papers) and [submission page](https://2027.ieee-iscas.org/submission) list the 13 October 2026 regular-paper deadline and 27 January 2027 final-paper deadline. As checked on 2026-09-09, neither page nor the one-page [IEEE CASS CFP](https://ieee-cas.org/files/ieeecass/2026-07/iscas2027-cfp.pdf) states the regular-paper page limit or exposes a final author kit. The working four-technical-pages plus one references-only page constraint is retained pending the final kit.
