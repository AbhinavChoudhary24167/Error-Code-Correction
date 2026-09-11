# Activity mapping diagnosis

Classification: **ACTIVITY_COVERAGE_BOTTLENECK_UNRESOLVED; ENERGY_NOT_QUALIFIED**.

This phase re-audits the immutable Attempt10 seed-11, upstream-original,
read-dominant diagnostic. It does not rerun or modify Attempt10 and does not
convert its tool power into energy/access. The checked component partition
reproduces the two aggregate report totals exactly:

| Architecture | Mapped partition | Unmapped partition | Aggregate |
|---|---:|---:|---:|
| U0 | 148 top ports + 148 data-macro pins | 310 I/O/hold-cell pins + 2 wire-buffer pins | 296/608 = 48.6842% |
| E0 | 142 top ports | 148 data-macro + 36 ECC-macro + 29 antenna + 320 I/O/hold + 2593 flattened-logic pins | 142/3268 = 4.3452% |

The CSV's `count_partition=true` rows are disjoint and sum to the aggregate.
Rows with `count_partition=false` expose required semantic classes that cannot
be counted separately in the flattened final netlist; they must not be added to
the aggregate denominator.

## Root cause by investigation axis

- **RTL-to-gate names and hierarchy.** The E0 RTL VCD contains nested scopes for
  `u_encoder`, `u_decoder`, `u_syndrome`, `u_data`, and `u_ecc`. The final E0
  netlist flattens most standard-cell instances to names such as `_458_` while
  retaining dotted macro instance names. Reading the RTL VCD at `tb/dut`
  therefore maps top-level ports only. U0 happens to retain an RTL-visible
  `u_data` macro scope, explaining its extra 148 mapped macro pins.
- **Optimized-away and transformed nets.** Synthesis canonicalization, logic
  optimization, I/O-fix insertion, hold repair, CTS, and routing create pins
  with no one-to-one RTL VCD identifier. The available report cannot distinguish
  optimized-away RTL nodes from newly inserted physical nodes.
- **VCD/SAIF.** The retained input is RTL VCD, not a gate-level VCD or a SAIF
  produced from the mapped netlist. No name-map file joining RTL objects to
  post-synthesis objects is retained. Changing only slash/dot syntax cannot map
  the generated standard-cell names.
- **SDF.** No mapped-gate simulation with SDF is retained. Consequently the
  activity lacks delay-dependent hazards and glitch energy. SDF annotation to
  the original hierarchical RTL would not solve the gate-instance name join.
- **Macro pins and internals.** U0 macro pins map; both E0 macro boundaries do
  not. Neither behavioral SRAM VCD exposes transistor/internal-node activity.
  Liberty conditional internal-power arcs can consume mapped boundary activity,
  but those arcs have not been independently power-validated.
- **Clock and sequential activity.** The clock is present at the top port, but
  mapped clock-tree and sequential pins are not separately covered. Attempt10
  reports zero U0 Clock power and nonzero E0 Clock power; neither is sufficient
  evidence of complete clock propagation.
- **Component attribution.** E0 encoder, syndrome/decoder, correction, control,
  and interconnect logic cannot be disjointly attributed after flattening. Any
  power split inferred from RTL toggle counts would ignore mapped capacitance,
  internal power, and glitches.

## What would resolve it

A qualifying run needs a mapped gate-level simulation of each exact final
netlist (or a proven synthesis name map), standard-cell simulation libraries,
SDF from the matching seed, a gate VCD/SAIF read into the matching ODB, and
retained annotated/unannotated reports by clock, sequential, combinational,
macro-boundary, encoder, decoder, and control classes. Five physical seeds and
both Liberty views must be joined by artifact hash. Macro read/write conditions
need isolated matched workloads and an independently validated internal-power
model. The disjoint power groups must reconcile to total power.

That experiment is not reproducible from the retained artifacts alone: the
necessary gate-level stimulus harness, cell simulation models, SDF/name map,
and component-preserving mapped hierarchy are absent. Therefore 100% relevant
coverage was not claimed and default/inferred activity remains excluded from
GREEN scoring.

## Immutable sources

- `A10_U0_ANNOTATED_LIST`: SHA-256 `e871811d0e639f987c27d4f4c108c67755ecd22d77a07e19d8e9209ca885b0f1`
- `A10_U0_UNANNOTATED_LIST`: SHA-256 `08143ec30284263baf043f668aac4ef6f965f371efe0c26deeb60c15bb199c9e`
- `A10_E0_ANNOTATED_LIST`: SHA-256 `1f2385a7cd04112615036596697b65a116735aed53c72fed4fceac31253cc4fb`
- `A10_E0_UNANNOTATED_LIST`: SHA-256 `c312498e2354e896ac245f7803c44138be2cf5b1e9091b3818caa53954e5f7c8`
- `A10_U0_FINAL_NETLIST`: SHA-256 `90db8ba99880047f277844cef511ea59a9072f0c0ec89101342a14f37f9bfb31`
- `A10_E0_FINAL_NETLIST`: SHA-256 `fb2aa6861d2f2203a3e1d622ed68d85d0658228d9621419453c98c4fe071605e`

The Attempt10 diagnostic used OpenROAD 26Q3-1080-gab6fd26351 in frozen image
`sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e`.
