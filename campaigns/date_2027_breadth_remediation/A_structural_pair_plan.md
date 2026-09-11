# Workstream A structural-pair plan

Plan status: `FROZEN_BEFORE_RTL_IMPLEMENTATION_OR_PHYSICAL_EXECUTION`

## Selected baseline identity

- Code ID: `hsiao-secded-72-64-v1`
- Hardware implementation ID: `hsiao-algorithmic-combinational-72-64-rev2-v1`
- Decoder module: `hsiao_secded_72_64_v2_algorithmic_decoder`
- Physical top: `gate04_rev2_hsiao_72_64`
- Encoder and syndrome implementation: qualified Revision-2 v1 modules, reused byte-exactly
- Transaction interface: the complete `gate04_rev2_hsiao_72_64` request/response interface
- Request latency: one cycle
- Initiation interval: one cycle

## Proposed additive structural identity

- Hardware implementation ID: `hsiao-hierarchical-nibble-decode-combinational-72-64-breadth-v1`
- New decoder module: `hsiao_secded_72_64_v3_hierarchical_decoder`
- New physical top: `breadth_hsiao_hierarchical_72_64`
- Expected request latency: one cycle
- Expected initiation interval: one cycle
- Intentional pipeline-depth change: none

## Exact intended structural change

The baseline decoder instantiates 72 logically independent equality relations between the eight-bit syndrome and the 72 frozen H-matrix columns. The new decoder will create shared one-hot decodes for the syndrome high nibble and low nibble. Each of the 72 column-match bits will be the conjunction of the corresponding shared high-nibble and low-nibble terms. The correction word, correction-applied flag, uncorrectable flag, and payload selection will retain the same equations.

The qualified encoder and syndrome source files will not be copied, edited, renamed, or replaced. Both physical identities will instantiate those exact existing files. The additive boundary will preserve the baseline boundary's ports, reset behavior, input register, output register, valid alignment, codeword echo, and status semantics.

This is scientifically meaningful because it changes the correction-selection network from a flat bank of 8-bit comparisons into a shared hierarchical decode/factorization, without changing the ECC matrix, code semantics, temporal organization, interface, latency, II, physical constraints, or backend policy. It is distinct from the existing combinational-versus-pipelined SECDED experiment.

The transformation will not be adjusted after physical results are observed. No synthesis attributes, technology primitives, pipeline registers, per-identity constraints, or result-dependent source edits are permitted.

## Exact equivalence relation

For every arbitrary 72-bit received word, the baseline and new decoder must produce equal:

- `data_out[63:0]`;
- `correction_applied`;
- `detected_uncorrectable`.

At the transaction boundary, for every arbitrary reset/valid/encoder-data/decoder-codeword input sequence from equal initialized state, the two identities must produce equal on the same cycle:

- `enc_valid_o` and `enc_codeword_o`;
- `dec_valid_o` and `dec_data_o`;
- `dec_codeword_echo_o`;
- `dec_detected_o`, `dec_corrected_o`, and `dec_uncorrectable_o`.

Temporal alignment is zero. Any required alignment is a qualification failure requiring investigation; it will not be accepted as an alternative proof relation.

## Formal proof strategy and hard gate

1. Hash-check all protected Revision-2 source identities against the Stage-0 inventory.
2. Use the frozen ORFS image's Yosys to elaborate both decoder cores and an additive mismatch miter.
3. Prove `mismatch == 0` by exhaustive SAT over an unconstrained 72-bit received word.
4. Elaborate both registered boundaries and use sequential SAT from equal zero initialization across reset and arbitrary request sequences to prove same-cycle equality of every output.
5. Record tool/image versions, exact commands, runtime, constraints/assumptions, source hashes, log hashes, and verdict in the new campaign only.

If either exact proof fails or is not assessable, `STRUCTURAL_PAIR_FORMAL_GATE = FAIL`, Workstream A stops, and no new structural identity is routed. The proof universe will not be weakened to weight-0/1/2 inputs.

## Synthesis structural sanity strategy

Only after formal PASS, run identical Yosys/SKY130HD synthesis scripts for the baseline and new physical tops. Preserve mapped cell-type histograms, total mapped cells, sequential cells, XOR/XNOR count, mux count, logic/hierarchy statistics available from the common tool, synthesized netlists, and hashes. The evidence will report honestly whether common synthesis collapses the intended distinction.

No synthesis setting may differ between the two identities. Synthesis distinctness will be judged from normalized mapped-netlist hashes and cell/hierarchy/cone evidence, not RTL text alone.

## Physical campaign strategy

Generate ten fresh 10 ns routes in the new campaign root, interleaved by seed:

1. seed 11 baseline, then new;
2. seed 13 baseline, then new;
3. seed 17 baseline, then new;
4. seed 19 baseline, then new;
5. seed 23 baseline, then new.

For both identities use the same frozen Revision-2 container digest, SKY130HD technology, `tt_025C_1v80` corner, 1.80 V, 25 C, 10 ns clock, 10,000 ps ABC period, 10% I/O delays, 0.05 pF loads, 35% utilization, aspect ratio 1.0, 10 um margin, placement density 0.55, one worker, LEC disabled, SDC methodology, trace policy, and seed mapping (`GPL_RANDOM_SEED = GRT_SEED = OR_SEED = seed`).

Each run keeps its exact result even if unfavorable. A physical failure is preserved and is not replaced by another seed. Power/energy is admitted only when the same timing/physical/evidence-join gates used by Revision-2 are satisfied.

Analysis will preserve per-seed values first and report descriptive mean, median, sample standard deviation, minimum, maximum, range, paired percentages, and ordering counts only. No population inference, p-values, or confidence intervals are authorized.
