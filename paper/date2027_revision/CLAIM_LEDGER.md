# DATE 2027 Claim Ledger

This ledger is the pre-draft claim boundary. Every manuscript statement must remain within one of the admitted scopes below. Quantitative claims are later expanded into `RESULT_PROVENANCE.csv` at per-seed granularity.

## A. PROVEN

| ID | Admitted statement | Proof boundary | Source |
|---|---|---|---|
| A1 | The combinational and pipelined SECDED (72,64) hardware identities implement the same systematic transaction relation after the documented two-cycle response alignment. | Universal encoder/decoder equivalence for the named frozen RTL pair; not equality of latency or internal state | `docs/date2027/rigour_gate_03r/SECDED_PROOF_SUMMARY.json`; `ENCODER_PROOF_MATRIX.csv`; `DECODER_PROOF_MATRIX.csv`; `H2_ARCHITECTURE_CONTRACT.md` |
| A2 | Both SECDED identities accept one useful operation per cycle (II=1); request latency is one cycle for combinational and three cycles for pipelined. | Frozen transaction and characterization-boundary contract | `docs/date2027/rigour_gate_03r/H2_ARCHITECTURE_CONTRACT.md`; `docs/date2027/revision2/REV2_MULTI_SEED_ENVIRONMENT.json` |
| A3 | The flat and hierarchical Hsiao decoders are equal for arbitrary 72-bit received words. | Unconstrained decoder miter | `campaigns/date_2027_breadth_remediation/formal/results/A_formal_qualification.json` |
| A4 | The registered flat and hierarchical Hsiao boundaries have same-cycle transaction equality from the specified all-zero initialization under arbitrary reset, valid, payload, and received-word sequences. | Temporal induction with zero alignment; no arbitrary-initial-state claim | Same as A3 |
| A5 | The Hsiao pair preserves encoder, parity-check matrix, interface, status behavior, latency, II, and register count while changing decode organization. | Frozen RTL/source contract plus formal and mapped-structure evidence | A3 source; `synthesis/A_synthesis_structural_comparison.json` |
| A6 | Qualified SECDED/Hsiao universes provide W1 correction and W2 detection; the evaluated BCH identity provides W1/W2 correction. | Exhaustive/formal code-qualification records for the named identities | Revision-2 qualification registry and breadth formal records |

## B. MEASURED

| ID | Admitted statement | Condition | Source |
|---|---|---|---|
| B1 | Ten 10 ns SECDED routes (five per identity) close setup, hold, route, and final DRC. | Frozen SKY130HD/TT/1.80 V/25 C physical contract | `REV2_MANUSCRIPT_EVIDENCE.json` |
| B2 | At 10 ns, mean SECDED area is 18,650 vs 25,588 um2 and detailed wire is 44,917 vs 49,964 um for combinational vs pipelined. | Five matched seeds | Same as B1 |
| B3 | At 10 ns, mean signed-slack-derived frequency estimates are 238.9 vs 350.0 MHz. | Five matched seeds; this is not measured Fmax | Same as B1 |
| B4 | At 10 ns, equal-work no-error energy is 145.77 vs 111.63 pJ/op. | 100,000 useful operations, II=1, routed ODB/SDC/SPEF and primary-input VCD | Same as B1 |
| B5 | The Hsiao pair is physically feasible in all ten 10 ns runs. | Five matched seeds per identity | `A_structural_pair_summary.json` |
| B6 | Hierarchical Hsiao has lower area in 5/5 seeds; higher cells, detailed wire, vias, and energy in 5/5; timing is higher in 4/5 and reverses once. | Exact structural pair at 10 ns | Same as B5 |
| B7 | SECDED mean internal power is 6.7533 vs 7.2104 mW, switching 7.8221 vs 3.9514 mW, and total 14.5754 vs 11.1618 mW. | Same qualified 10 ns trace and routed identities | `B_power_components_summary.json` |
| B8 | All ten fresh 5 ns SECDED implementations are route-complete, DRC-clean, hold-clean, setup-feasible, and power-eligible. | Prospectively frozen 5 ns target | `C_5ns_summary.json` |
| B9 | The evaluated BCH(78,64,t=2) syndrome/Chien identity has mean area 57,240 um2, signed setup slack about -5.01 ns, about 66 setup violations per seed, and 0/5 target feasibility at 10 ns. | Physical quantities from completed routes; target-clock energy ineligible | `REV2_MANUSCRIPT_EVIDENCE.json` |

## C. DERIVED

| ID | Admitted statement | Derivation |
|---|---|---|
| C1 | SECDED pipeline relative to combinational at 10 ns: area +37.2%, wire +11.2%, timing metric +46.6%, energy/op -23.4%. | Pair each seed before averaging: `100*(changed-baseline)/baseline` |
| C2 | Hierarchical relative to flat Hsiao at 10 ns: area -0.564%, cells +0.276%, wire +3.867%, vias +3.918%, timing +2.656%, energy/op +1.328%. | Same paired-percent rule |
| C3 | SECDED component effects: internal +6.77%, switching -49.48%, leakage +34.43%, total/energy -23.4%; absolute mean differences are +0.4571, -3.8707, and -3.4136 mW for internal, switching, and total. | Paired component differences from qualified power records; absolute deltas share additive units |
| C4 | SECDED cell-group effects: combinational -55.50%, sequential +70.86%, clock +74.34%. | Paired group-total differences |
| C5 | SECDED pipeline relative to combinational at 5 ns: area +36.7%, cells +27.9%, wire +12.8%, vias +18.6%, timing +68.6%, energy/op -19.3%. | Same paired-percent rule over five seeds |
| C6 | `f_slack = 1000/(T-s_setup)` MHz is a post-route signed-slack-derived frequency estimate. | Algebraic transformation of target period and signed worst setup slack |
| C7 | `E_op = P_total*t_trace/N_useful`. | Equal-work energy normalization |

## D. INTERPRETATION

| ID | Admitted statement | Boundary |
|---|---|---|
| D1 | The temporal SECDED change creates a large mixed, non-dominated area-latency-timing-energy trade-off. | Objectives must be named; the pipeline does not dominate because area and latency worsen |
| D2 | The Hsiao refactoring creates a modest mixed physical displacement. | Small effect is retained and not magnified; one timing reversal remains visible |
| D3 | Exact semantic equality requires separate physical measurement but does not predict effect magnitude. | Synthesis of A1-A5 with B1-B6 |
| D4 | Switching is the largest reported top-level component difference behind the SECDED energy reduction. | Absolute-difference accounting statement, not per-net causality |
| D5 | Tighter implementation constraint preserves the temporal trade directions while changing magnitudes. | Limited to 10 ns vs fresh 5 ns implementations in one technology/corner |
| D6 | The evaluated BCH realization is a stronger-correction feasibility boundary. | Identity-scoped; no BCH-family ranking |
| D7 | Matched seeds test sensitivity to deterministic physical heuristics. | They do not represent fabricated chips, process samples, or population inference |
| D8 | Implementation identity is a measurement requirement, not an effect-size predictor. | Central bounded implication |

## E. HYPOTHESIS

| ID | Permitted wording | Missing evidence |
|---|---|---|
| E1 | Glitch suppression is one possible explanation among changes in activity, capacitance, buffering, and placement. | Per-net delay-aware waveform evidence and controlled ablations sufficient for causal attribution |
| E2 | Register insertion, logic partitioning, buffering, and placement may jointly contribute to the observed temporal displacement. | Controlled ablations isolating each mechanism |

## F. PROHIBITED

| ID | Prohibited statement | Why prohibited |
|---|---|---|
| F1 | Pipelining improves SECDED / universally reduces ECC energy. | Area and latency worsen; one workload, node, corner, and two targets do not support universality |
| F2 | Pipelining reduces glitches by a measured percentage. | Aggregate component power does not establish a per-net causal mechanism |
| F3 | The reported timing metric is measured or achieved Fmax. | No frequency search or reimplementation establishes maximum frequency |
| F4 | The five seeds establish statistical significance, process variation, or population robustness. | Seeds are deterministic heuristic perturbations only |
| F5 | BCH is inherently slow or impractical. | One syndrome/Chien identity misses one common target |
| F6 | Hsiao structural change is negligible or always beneficial/harmful. | Mixed small effects and one timing reversal contradict categorical ranking |
| F7 | Route completion implies target feasibility. | Setup, hold, violations, and DRC are separate gates |
| F8 | Target-clock BCH energy is zero or comparable. | Measurement is ineligible/unavailable, not zero |
| F9 | The study provides a family-wide ECC ranking or silicon energy. | Scope is frozen codec RTL and estimated post-route activity power |
| F10 | The 5 ns campaign is DVFS or technology portability. | Voltage, technology, corner, and RTL remain fixed |
| F11 | Sustainability, lifecycle carbon, FIT/SER, or SRAM-macro conclusions follow from this paper. | Those belong to a distinct research direction and evidence boundary |
