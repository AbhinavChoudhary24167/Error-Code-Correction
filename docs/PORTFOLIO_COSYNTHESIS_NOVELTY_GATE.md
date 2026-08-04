# Portfolio co-synthesis novelty gate

Status: **conditional go for a falsifiable prototype, not a publication novelty claim**  
Review date: 2026-08-03  
Scope reviewed: binary short-block SRAM codes, probability-weighted error-pattern protection, SDC-constrained decoding, and hardware sharing across a reconfigurable code portfolio.

## Decision

The broad ideas in the proposed phase are not new in isolation:

- automatic construction and formal synthesis of Hamming/FEC generators;
- probability- or application-weighted code objectives;
- Hamming/Hsiao matrix selection for hardware power, area, and delay;
- fault-pattern-specific memory codes such as SEC-DAEC and TAEC;
- adaptive or reconfigurable memory protection;
- joint code/encoder/decoder design for LDPC systems; and
- common-subexpression sharing across a family of standardized encoders.

The closest reviewed work, *Towards Synthesis of Application-Specific Forward
Error Correction Codes*, is especially important: it uses SMT/CEGIS to synthesize
Hamming generators from user properties, exposes a weighted objective, and
demonstrates combinations of generators. Its future-work section explicitly
discusses combining codes and multi-bit correction. Therefore GREEN-ECC must not
claim that application-specific synthesis, probability weighting, or generating
multiple codes is itself new.

The technically distinct, testable target retained by this gate is:

> Jointly modify a small portfolio of systematic short-block SRAM parity-check
> matrices and one shared encoder/syndrome/correction hardware graph, using an
> explicit error-pattern PMF, while enforcing decoder-executed SDC limits and
> publishing exhaustive outcome certificates and distribution-shift envelopes.

The distinction is the conjunction, not any individual ingredient:

1. the probability domain is an enumerated SRAM error-vector PMF rather than a
   uniform channel label or application data-value importance alone;
2. SDC is evaluated by executing the actual bounded-distance syndrome decoder
   on every modeled vector and is a hard constraint;
3. matrices are altered while the cost of a shared multi-mode XOR/syndrome and
   correction fabric is in the synthesis loop;
4. externally supplied matrices use the same independent verifier and artifact
   format; and
5. deployment is rejected outside a validated distribution envelope or when
   the existing transition-aware scheduler cannot amortize hardware and
   migration costs.

This is a **conditional go** because the literature search did not identify a
primary work that demonstrates that exact combination. It is not proof of
novelty: a broader systematic review, citation chasing, patent review, and expert
assessment remain necessary before submission.

## Primary-literature comparison

Legend: “partial” means the paper addresses a related metric or architecture but
does not implement the full column requirement used here.

| Prior work | Generates H? | Uses fault PMF? | Controls SDC? | Models hardware during code generation? | Synthesizes multiple codes jointly? | Shares hardware across codes? | Main difference from the gated target |
|---|---:|---:|---:|---:|---:|---:|---|
| [McClurg et al., *Towards Synthesis of Application-Specific FEC Codes*, HotNets 2024](https://doi.org/10.1145/3696348.3696886) | Yes | Partial: weighted bit/application objective | No hard decoder-executed SRAM SDC bound shown | Partial: generator size/implementability properties | Partial: generator combinations and bit mapping | No demonstrated shared portfolio fabric | Closest synthesis work; not SRAM error-vector PMFs, shared multi-mode decoder hardware, or deployment envelopes. |
| [Ghosh, Basu, and Touba, *Reducing Power Consumption in Memory ECC Checkers*, ITC 2004](https://doi.org/10.1109/TEST.2004.1387407) | Selects/optimizes SEC-DED H | No; workload switching traces | No | Yes: power, area, delay | No | No | Optimizes one Hamming/Hsiao checker rather than PMF protection or a shared portfolio. |
| [Basak et al., *Reconfigurable ECC for Adaptive Protection of Memory*, MWSCAS 2013](https://doi.org/10.1109/MWSCAS.2013.6674841) | No | Reliability state, not enumerated PMF synthesis | No | Architecture evaluated after choosing codes | No | Reconfigurable protection architecture | Selects protection strength spatially/temporally; does not synthesize portfolio matrices and shared logic together. |
| [Shin et al., *Adaptive ECC for Tailored Protection of Nanoscale Memory*, IEEE Design & Test 2017](https://doi.org/10.1109/MDAT.2016.2615844) | No | Runtime failure/reliability state | No | Reconfigurable hardware is evaluated | No | Yes, adaptive hardware | Tailors existing protection at runtime; does not generate PMF-specialized matrices with SDC certificates. |
| [Luo et al., CREAM, *Using ECC DRAM to Adaptively Increase Memory Capacity*](https://arxiv.org/abs/1706.08870) | No | No enumerated fault PMF | No | Yes, capacity/performance layouts | No | Uses existing ECC/parity modes | Trades DRAM reliability for capacity using catalogue modes rather than co-synthesized codes. |
| [Zhang et al., *Chameleon: An Adaptive Thermal-Aware ECC Scheme*, IEEE TVLSI 2019](https://doi.org/10.1109/TVLSI.2019.2913207) | No | Temperature-dependent reliability, not error-vector PMF synthesis | No | Adaptive cache hardware evaluated | No | Adaptive strength | Temperature selects existing strengths; no matrix/shared-graph synthesis or exhaustive SDC classification. |
| [Kim et al., *Unity ECC*, SC 2023](https://doi.org/10.1145/3581784.3607081) | Manually constructs a code | Fault classes, not a synthesis PMF | Discusses reliability, not a synthesis-time SDC constraint | Yes | No | Unifies protection in one code | Exploits unused syndromes for chip/double-bit errors; does not synthesize a regime portfolio or shared reconfigurable graph. |
| [Jun and Lee, *SEC-DED-DAEC With No Mis-correction*, ELEX 2013](https://doi.org/10.1587/elex.10.20130743) | Constructs H | Pattern class, not PMF mass | Yes for specified non-adjacent miscorrections | Hardware compared | No | No | Hand-designed adjacent-error code; no probability-weighted portfolio co-synthesis. |
| [Reviriego et al., *Low Delay SEC-DAEC Codes*, Microelectronics Reliability 2019](https://doi.org/10.1016/j.microrel.2019.03.012) | Constructs H | Pattern class, not PMF mass | Partial | Yes: decoder delay guides construction | No | No | Hardware-aware single-family construction without PMF/SDC portfolio optimization. |
| TAEC and burst/MBU-oriented memory-code literature, including the adjacent-error decoder line summarized by [Maity et al.](https://doi.org/10.1049/iet-cdt.2019.0268) | Often | Usually pattern classes | Varies | Often after or during construction | No evidence found | No evidence found | Establishes fault-pattern-specific matrices; pattern specialization alone is not the contribution. |
| [Zhong and Zhang, *Joint Code-Encoder-Decoder Design for LDPC VLSI*, ISCAS 2004](https://sites.ecse.rpi.edu/~tzhang/pub/ISCAS04_2.pdf) | Yes | Channel statistics, not bounded SRAM vector PMF | No SRAM SDC constraint | Yes | No portfolio | No | Strong prior art for hardware-aware code construction, but targets long irregular LDPC communication codes. |
| [Mahdi et al., *A Multirate Fully Parallel LDPC Encoder*, IEEE TVLSI 2021](https://doi.org/10.1109/TVLSI.2020.3034046) | No; standardized matrices | No | No | Yes | Treats a code set jointly in hardware | Yes, common XOR subexpressions | Strong prior art for sharing across codes; matrices are fixed rather than co-synthesized under SRAM PMFs and SDC constraints. |
| [Sani et al., *A Dynamically Reconfigurable ECC Decoder Architecture*, DATE 2016](https://past.date-conference.com/proceedings-archive/2016/pdf/0196.pdf) | No | No | No | Yes | Supports multiple decoder configurations | Reconfigurable network | Demonstrates programmable ECC hardware but not SRAM matrix/PMF co-synthesis. |
| [Application-specific memory protection policies, RSP 2015](https://doi.org/10.1109/RSP.2015.7416541) | No | Application vulnerability, not error-vector PMF synthesis | No | Selective-ECC/VFS system cost | No | No | Allocates protection policies rather than creating codes. |
| [BEER: Bit-Exact ECC Recovery](https://doi.org/10.1145/3373376.3378458) | Recovers an unknown H | Uses retention behavior for inference | Characterizes miscorrection behavior | No generation objective | No | No | Recovers deployed on-die ECC; valuable verifier/input use case, not synthesis. |

## Research questions and falsifiers

### RQ1 — single-code generation

Claim tested: under equal `(k,r)`, explicit PMF optimization can reduce
probability-weighted residual failure or SDC relative to conventional matrices.

Kill criterion: no improvement across diverse PMFs, or improvement requires an
unacceptable SDC increase.

### RQ2 — portfolio generation

Claim tested: a small portfolio can dominate both a general-purpose matrix and
selection from the available fixed catalogue.

Kill criterion: one generated matrix matches the portfolio, or gains appear only
for a single convenient synthetic PMF.

### RQ3 — hardware co-synthesis

Claim tested: changing matrices in response to shared-graph cost produces a
smaller structural or synthesized implementation than sequential generation,
separate engines plus MUXes, and a programmable crossbar.

Kill criterion: Yosys/ABC or another synthesis flow eliminates the apparent
sharing advantage, or configuration/MUX/correction-table costs dominate it.

### RQ4 — distribution shift

Claim tested: certified validation envelopes plus fallback bound SDC under PMF
shift.

Kill criterion: small plausible shifts violate SDC/FIT constraints or cause
frequent fallback that removes the nominal benefit.

### RQ5 — deployment

Claim tested: at least one credible trace amortizes shared hardware and migration
cost through the existing transition-aware scheduler.

Kill criterion: the best generated matrix should remain fixed, or migration and
reconfiguration erase all portfolio benefit.

## Scope boundary

The first implementation is restricted to binary systematic linear block codes,
hard-decision syndrome decoding, a common `(k,n,r)` per portfolio, and finite
enumerated error universes. Small instances may be solved exactly by exhaustive
Boolean enumeration when no SAT/SMT package is installed. Scaling uses a
deterministic search, but every output must pass an independent exact verifier.

No claim is made about soft-decision codes, arbitrary BCH/LDPC construction,
continuous analog faults, all SRAM technologies, or optimal physical PPA.

## Gate requirements before broad implementation

Stage 1 may proceed only if it produces all of the following:

1. systematic `H=[P^T|I]` and `G=[I|P]` matrices;
2. exact GF(2) rank and `G H^T = 0` checks;
3. an explicit syndrome-to-correction map;
4. exhaustive execution of the decoder for every data word and modeled error;
5. probability-mass totals for corrected, DUE, SDC, and decoder failure;
6. solver status, search coverage, runtime, timeout, and optimality statement;
7. a machine-readable certificate validated independently of the generator.

Only a passing, reproducible Stage 1 certificate justifies Stage 2.

## Claims prohibited at this gate

- “first automatic ECC synthesizer”;
- “first application- or probability-specific ECC”;
- “first hardware-aware parity-check matrix optimization”;
- “first adaptive/reconfigurable memory ECC”;
- “first shared multi-code encoder/decoder”;
- physical area, delay, power, energy, leakage, or carbon improvement without
  an available synthesis flow and characterized library;
- robustness to measured SRAM faults when the benchmark PMFs are synthetic;
- superiority at `k=64` before verified scaling evidence exists.

