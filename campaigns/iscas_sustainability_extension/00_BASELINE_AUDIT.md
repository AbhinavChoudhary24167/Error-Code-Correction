# Gate 0 — DATE baseline audit

## Verdict

**PASS.** The final DATE Revision-3 baseline is protected at commit
`9968f9b15f949d38faf944a3546ea736cfab63df`, with its qualified physical
evidence inherited from commit `b51291442bbd04346dac939dea6ba7d532b9c5c4`.
The new work is isolated on branch `codex/ecc-lifecycle-sustainability` under
`campaigns/iscas_sustainability_extension/`. No protected DATE file was
modified.

The required numerical reconstruction produced 40 run-level records and 13
independent paired-effect checks. Every reconstructed mean agrees with its
qualified machine-readable source to within `1e-9` percentage point and with
the rounded values in the research brief. There is no numerical discrepancy
requiring the campaign to stop.

### Validation record

- `python3 -m pytest -q campaigns\iscas_sustainability_extension\tests`: **5 passed**.
- `make`: **PASS**.
- `make test`: the C++/CLI checks passed; repository Python tests ended with
  **482 passed, 2 failed**. Both failures are frozen Gate-03 scope guards whose
  historical allowlists intentionally reject the new
  `campaigns/iscas_sustainability_extension/` path.
- `python3 -m pytest -q`: **483 passed, 3 failed**. Two are the same frozen
  scope guards. The third was a Windows resource incident (`DLL load failed`;
  paging file too small) in one golden CLI subprocess. Re-running exactly
  `test_golden_select_outputs` in isolation gave **1 passed**, confirming that
  the golden output contract itself is intact.

The old scope validators were not broadened because they are protected DATE
baseline artifacts. Their failures classify the unmodified historical guard,
not the Gate-0 evidence. Final protected-scope revalidation still reports zero
changed, missing, or added files in all 7,094 protected records.

## 1. Repository structure

The frozen commit contains 2,327 tracked files. The parts relevant to this
extension are:

| Path | Role | Gate-0 assessment |
|---|---|---|
| `asic/` | Synthesizable ECC RTL, SRAM-style behavioral arrays/wrappers, and testbenches | Reusable RTL; no compiled SRAM macro |
| `scripts/gate03r/`, `scripts/gate04/`, `scripts/revision2/` | Formal, trace, OpenROAD/ORFS, power, and analysis flows | Primary reusable physical infrastructure |
| `docs/date2027/revision2/` | Qualified five-seed physical result tables, environment freeze, and Hsiao qualification | Authoritative 10 ns run evidence |
| `campaigns/date_2027_breadth_remediation/` | Structural-Hsiao pair, power decomposition, and 5 ns condition campaign | Authoritative extension evidence |
| `paper/date2027_revision3/` | Final Revision-3 manuscript, generated tables/figures, and claim registry | Final DATE interpretation layer |
| `green_ecc_physical_simulation/registry/` | Code, implementation, architecture, and scenario records | Reusable identity/provenance vocabulary |
| `codeforge/placement_policy.py` | Finite logical data-column permutation library | Reusable concept only; not a physical SRAM map |
| `analysis/`, `carbon*.py`, `energy_model.py` | Existing analytical, sensitivity, and carbon utilities | Reusable after evidence-boundary review; current coefficients are not the new lifecycle model |
| `tests/` | Functional, schema, physical-evidence, and CLI regression tests | Reusable regression foundation |
| `reports/`, `docs/`, `paper/` | Generated and frozen prior evidence | Protected input, never an output target for this campaign |

There are no tracked `.lef`, `.gds`, Liberty `.lib`, `.sp`/`.spice`, `.odb`,
`.spef`, or VCD files. The large physical artifacts are intentionally retained
outside Git in two immutable WSL evidence roots.

## 2. Protected DATE baseline

There are three distinct freeze layers and they must not be conflated:

1. `DATE2027_MANUSCRIPT_FREEZE.json` protects the earlier submission package.
2. Commit `b51291442bbd04346dac939dea6ba7d532b9c5c4` freezes the qualified five-seed physical/breadth evidence.
3. Commit `9968f9b15f949d38faf944a3546ea736cfab63df` is the exact final Revision-3 paper state that reports the values named in the new brief.

Gate 0 therefore selects layer 3 as the completed DATE baseline and records
layer 2 as the physical-evidence commit. The byte manifest protects:

| Scope | Files | Tree SHA-256 |
|---|---:|---|
| Repository files at `9968f9b…` | 2,327 | `9d898cd01f3f654b8d94daab8649213f2e4477ef4250caa2240736a3d2993ee2` |
| `/var/lib/green-ecc-date2027-revision2` | 2,366 | `aef82cd7b54dc9b939d705ae46edd09a87506e74ed3e4ab5e9e857daeb1e172d` |
| `/var/lib/green-ecc-date2027-breadth-remediation` | 2,401 | `ccf2227275b8e6f2ab5bae747485e14dcc320e7df6fc33bef3ebc0cfd774ba7d` |
| **Total** | **7,094** | Per-scope roots above |

Revision-2 was revalidated silently against its already-qualified 2,366-file
GNU `sha256sum` manifest. The breadth root was freshly read and SHA-256 hashed
file by file. This distinction is recorded in
`baseline_integrity_manifest.json` because a monolithic WSL/Python traversal of
the older ext4 tree caused a host interop failure; the underlying qualified
`sha256sum --status -c` verification passed.

## 3. Exact artifacts available

### Repository-resident evidence

- Final Revision-3 claim registry, tables, figures, source, PDF, and evidence registry.
- Five-seed Revision-2 run CSV/JSON, architecture summaries, paired effects, environment freeze, and manuscript-evidence registry.
- Five-seed structural-Hsiao per-run records, summary, formal SAT/temporal-induction logs, and mapped synthesis outputs.
- Five-seed 5 ns SECDED per-run records and summary.
- Full-precision SECDED internal/switching/leakage and hierarchical power decomposition.
- Formal and exhaustive qualification records for the admitted SECDED, Hsiao, and BCH identities.

### Immutable raw evidence

| Root | Final ODB | Final SPEF | Final GDS | Full-precision power reports | Input VCDs |
|---|---:|---:|---:|---:|---:|
| Revision-2 raw root | 20 | 20 | 20 | 15 | 9 |
| Breadth raw root | 20 | 20 | 20 | 20 | 2 |

Each run also retains final Verilog, SDC, DEF, logs, reports, effective
environment, command records, run metadata, and `raw-artifacts.sha256`.
`baseline_results.csv` resolves every admitted run to its RTL aggregate hash,
formal evidence, target, seed, PPA/power/energy fields, final
ODB/netlist/SDC/SPEF hashes, power-report hash, raw-manifest hash, and external
artifact root. Missing BCH power/energy fields remain empty because the BCH
implementation is timing-ineligible at 10 ns; they were not imputed.

## 4. Existing qualified ECC implementations

| Hardware identity | Code identity and guarantee | Latency / II | Qualified physical conditions | Status |
|---|---|---:|---|---|
| `secded-rtl-combinational-72-64-v1` | Extended-Hamming `(72,64)`; W1 correct, W2 detect | 1 / 1 | 10 ns and 5 ns, seeds 11/13/17/19/23 | Feasible 5/5 at each target |
| `secded-rtl-pipelined-72-64-v1` | Same exact code/decoder behavior | 3 / 1 | 10 ns and 5 ns, same seeds | Feasible 5/5 at each target |
| `hsiao-algorithmic-combinational-72-64-rev2-v1` | Hsiao `(72,64)`; W1 correct, W2 detect | 1 / 1 | 10 ns, Revision-2 and fresh structural campaign | Feasible 5/5 |
| `hsiao-hierarchical-nibble-decode-combinational-72-64-breadth-v1` | Exact-equivalent Hsiao hierarchical decoder | 1 / 1 | 10 ns, seeds 11/13/17/19/23 | Feasible 5/5 |
| `shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1` | BCH `(78,64,t=2)`; W1/W2 correct | 1 / 1 | 10 ns, seeds 11/13/17/19/23 | Routed 5/5, target-feasible 0/5 |

The repository also contains SEC-DAEC, TAEC, Polar, cyclic/BCH reference,
generated-width, SafeForge, and SRAM-wrapper RTL/software identities. Those are
not automatically admitted to this campaign: several have bounded,
reference-only, projected, rejected, or otherwise non-comparable evidence.
Gate 8 must create a new qualification record for any stronger hardware point.

## 5. Existing power and VCD infrastructure

The qualified flow uses OpenSTA on final routed ODB/SDC/SPEF, reads a
primary-input VCD at scope `gate04_trace_top`, propagates activity, and emits
`report_power -digits 12`. The environment is pinned to:

- `openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e`;
- ORFS `56496f3980fb6e9e58f10c8aea4a98949c0fe5f2`;
- OpenROAD `ab6fd26351dc449e69059684dc6aa9ae9046eb36`;
- SKY130HD `tt_025C_1v80`, 1.80 V, 25 °C;
- one worker, 35% requested core utilization, 0.55 placement density, and matched seeds `11,13,17,19,23`.

Nine deterministic 10 ns traces already exist: W0, W1, and W2 for conventional
SECDED, Hsiao, and BCH. Every trace has 100,000 useful operations, payload seed
`104375203646206`, and fault-schedule seed `7085774586302733229`. The activity
auditor records signal-level value changes and bit transitions.

The critical evidence boundary is:

- **Available input activity:** W0, W1, W2.
- **Qualified post-route power:** W0 only.
- **Not yet available:** A2C power, controlled mixed traffic, action-separated correction/detection energy, and retained per-net evidence adequate for a glitch-suppression claim.

The W1/W2 traces are reusable starting points, not energy measurements.

## 6. SRAM-related infrastructure already present

The repository contains:

- a synthesizable registered-read behavioral array, `asic/common/sram_core.sv`;
- ECC-facing wrappers/tops for SECDED, SEC-DAEC, TAEC, BCH, and Polar;
- a C++ `PracticalSRAMSimulator` and Python workflow/benchmark adapters for 64/128/256 KiB and 8/16/32-bit software studies;
- projected selector, area, energy, reliability, and ML-advisory interfaces;
- Qcrit/fault-distribution data and analytical scenario records.

These assets are useful for interface semantics, workload generation, and
software cross-checks. They do **not** constitute a compiled SRAM macro or a
measured SRAM+ECC boundary. The tracked repository contains no SRAM LEF, GDS,
Liberty, SPICE, macro characterization, extracted macro parasitics, or macro
access-energy table.

The existing `codeforge/placement_policy.py` does enumerate finite even/odd and
other logical data-column permutations within one codeword. Its cost is an
index-displacement proxy and its own documentation excludes routed-wire claims.
It cannot represent a physical adjacent W4 cluster becoming four W1 events in
four codewords. It is a reusable test/reference concept, not the required
physical row/column/bank/subarray-to-codeword mapping.

## 7. OpenRAM and other compiler infrastructure

OpenRAM is neither installed on Windows nor importable/installed in the WSL
environment. No OpenRAM configuration, generated macro, technology plug-in, or
compiler-specific script is tracked. No other memory compiler is integrated.
The pinned OpenROAD Docker image is locally available, but OpenRAM must be
surveyed and qualified separately at Gate 3.

Gate 3 must investigate OpenRAM first and then evaluate independent candidate
ecosystems. A second compiler/macro source will be admitted only if useful
capacity, technology/PDK, corner, voltage, temperature, word organization, and
LEF/GDS/Liberty/SPICE semantics permit a fair comparison. An incompatibility
table is a valid result; a mixed-technology numerical ranking is not.

## 8. Reusable assets

- Exact identity contracts, formal miters, SAT proof patterns, and latency/II accounting.
- Frozen matched-seed set and interleaved run order.
- ORFS/OpenROAD physical policy, write-once external evidence layout, per-run manifests, and raw-artifact hashing.
- Final ODB/SDC/SPEF and no-error power flow for activity-only re-analysis without rerouting.
- Deterministic payload/error trace seeds and W0/W1/W2 VCD generators/auditor.
- Full-precision component and hierarchical power parsers.
- 64-bit payload baseline and existing SRAM workload sizes as inputs to—not substitutes for—the macro-organization decision.
- Logical placement candidate code and fault-universe machinery as unit-test references.
- Existing sensitivity, Pareto, workload, and carbon utilities after their projected/calibrated fields are kept separate from new measured inputs.

## 9. Missing evidence and infrastructure

1. W1/W2/mixed post-route power for the qualified identities.
2. Per-net retained activity/power evidence sufficient to test a glitch mechanism.
3. A compiler survey and any qualified SRAM macro views.
4. A fair SRAM data/parity organization and equal-useful-capacity contract.
5. Physical row/column/bank/subarray coordinates and cross-codeword interleaving factors 1/2/4.
6. A spatial injector that maps physical clusters to per-codeword W0/W1/W2/W3+ outcomes.
7. Measured interleaving mux/routing/control overhead.
8. A timing-feasible qualified stronger-correction implementation.
9. A non-overlapping SRAM+ECC read/write/action energy boundary.
10. Sourced, versioned embodied-carbon parameters and separate uncertainty categories.
11. Break-even solvers and phase maps driven only by admitted evidence.
12. A second comparable physical/macro condition.

Operational risk: the Windows `C:` volume fell as low as about 242 MB free
during Gate 0 (and later recovered after test cleanup). Future raw traces,
macro views, and route databases must remain in a
new write-once WSL evidence root with only compact manifests/summaries committed
to this repository. Gate 1 must fail closed if adequate external capacity is
not confirmed.

## 10. Exact execution plan for Gates 1–12

### Gate 1 — Activity-trace infrastructure

Freeze an action vocabulary (`A0`, `A1`, `A2`, `A2C`, `AMIX`), useful-operation
definition, deterministic seeds, trace scope, reset/warm-up/flush policy, and
equal-work validator. Revalidate the existing W0/W1/W2 traces, generate only
missing A2C/mixed traces, and create write-once trace manifests. **Pass:** all
eligible identities have hash-stable traces with exactly equal useful work and
functional action counts. **Dependency:** Gate 0 PASS.

### Gate 2 — W0/W1/W2 physical power

Read the protected final ODB/SDC/SPEF artifacts without changing them and write
new full-precision power, annotation, hierarchical, and where practical per-net
reports under the new external root. Use paired seeds 11/13/17/19/23 and reject
timing-ineligible operating-point energy. **Pass:** complete admissible paired
tables for clean/W1/W2/mixed traffic, with no substituted seed and no unequal
operation count. **Dependency:** Gate 1 PASS.

### Gate 3 — Memory-compiler feasibility

Survey OpenRAM first, then credible independent open macro/compiler ecosystems.
Record license, maintenance state, technologies, depth/width support, generated
LEF/GDS/Liberty/SPICE/netlist views, characterization, OpenROAD/OpenSTA
compatibility, and reproducibility. Freeze a comparability rubric before
selection. **Pass:** one viable primary compiler; **conditional pass:** only
OpenRAM is comparable and the second source is explicitly ineligible; **fail:**
no mutually usable macro views. **Dependency:** Gate 0 PASS; may run in parallel
with Gates 1–2 after its survey contract is frozen.

### Gate 4 — SRAM generation and characterization

Infer the first useful capacity from the 64-bit payload boundary and existing
64/128/256 KiB workload domain; do not select a size merely because a compiler
example supports it. Freeze data/parity macro organizations, generate read-only
views, validate view consistency, integrate macros into OpenROAD/OpenSTA, and
retain read/write energy, leakage, access time, geometry, and hashes. **Pass:**
at least one complete macro realization at an admitted corner. **Dependency:**
Gate 3 PASS/conditional pass.

### Gate 5 — Physical/logical interleaving model

Implement an explicit bijection over `(macro, bank, subarray, row, column)` to
`(logical word, codeword, codeword-bit)`. Freeze factors 1/2/4 and require a
unit witness in which an adjacent physical W4 maps to W4 in one word for factor
1 and four W1 events in four words for a suitable factor 4. Retain padding and
unused coordinates explicitly. **Pass:** deterministic round-trip mappings and
golden coordinate tests. **Dependency:** Gate 4 macro organization; abstract
geometry work may begin after its contract is frozen.

### Gate 6 — Spatial fault to reliability outcome

Inject single cells, horizontal/vertical pairs, bursts, rectangles, and
Manhattan clusters over valid macro coordinates; preserve boundary clipping and
bank/subarray crossings. Emit event-level mappings, per-codeword error weights,
and conditional corrected/detected/uncorrectable/silent outcomes. Report only
`P(outcome | geometry)` until a separate rate model is admitted. **Pass:**
exhaustive small-array and analytical witness tests agree. **Dependency:** Gate
5 PASS and qualified code semantics.

### Gate 7 — SRAM+ECC combined model

Define non-overlapping read/write/clean/correct/detect boundaries. Combine
macro access energy, redundancy storage, ECC logic, control, and measured
interleaving overhead at equal useful capacity. Map Gate-6 action distributions
to Gate-2 action energies without losing macro, seed, target, or trace identity.
**Pass:** every total is reconstructable from non-overlapping components and
all unavailable values remain null. **Dependencies:** Gates 2, 4, and 6 PASS.

### Gate 8 — Stronger-correction hardware

Profile the frozen BCH critical path, predeclare a bounded set of identities
(pipelined syndrome, staged/parallel/partially-parallel Chien variants), and
preserve the `(78,64,t=2)` guarantee. Apply functional, exhaustive/formal,
latency/II, synthesis, route, timing, and action-power gates. **Pass:** at least
one timing-feasible qualified stronger point; **conditional pass:** bounded
attempts all fail and the negative result is fully retained. **Dependencies:**
Gate 1 for activity and Gate 0 identity evidence.

### Gate 9 — Lifecycle carbon model

Create versioned assumption files with value, unit, source, range, rationale,
and applicability for embodied and operational terms. Keep PnR-seed variation,
fault-distribution uncertainty, and carbon-input uncertainty as separate axes.
Prefer parametric area/yield/wafer formulations when absolute manufacturing
data are weak. **Pass:** unit-checked model, sourced inputs, and no arbitrary
single-score collapse. **Dependency:** Gate 7 system boundary; source survey can
begin earlier under a frozen schema.

### Gate 10 — Break-even and phase boundaries

Solve the lifecycle difference equation for access count, lifetime,
utilization, and grid intensity, with action probabilities parameterized by
physical geometry/interleaving/ECC. Verify analytic solutions against numerical
sweeps and preserve no-crossing/infinite/undefined cases. Generate phase maps
only from machine-readable inputs. **Pass:** reproducible boundary tables with
unit tests and traceable optimal regions. **Dependencies:** Gates 7 and 9; Gate
8 adds stronger-ECC surfaces when available.

### Gate 11 — Additional physical condition

Admit a second PVT/library/memory source only through a frozen compatibility
contract. Repeat matched comparisons without claiming technology portability
from incomparable macros. Quantify movement of boundaries rather than pooling
conditions. **Pass:** at least one additional comparable condition;
**conditional pass:** incompatibility is documented and no false ranking is
made. **Dependencies:** Gates 3–4 and the relevant Gate-2/7 flow.

### Gate 12 — Final integrity and reproducibility audit

Re-run the 7,094-file baseline manifest, verify every new stage manifest and
raw hash, run `make`, `make test`, and `python3 -m pytest -q`, regenerate all
tables/figures from raw data, and produce the required final evidence/status,
claim map, limitations, reproduction, and baseline-integrity documents. Do not
start a manuscript until this gate closes. **Pass:** zero protected changes,
all viable dependency gates correctly classified, and every proposed claim has
admitted evidence.

## Reconstructed baseline values

| Result | Independent reconstructed mean |
|---|---:|
| Temporal SECDED 10 ns area | +37.2018636927% |
| Temporal SECDED 10 ns timing | +46.6293549822% |
| Temporal SECDED 10 ns energy/op | −23.4190052226% |
| Temporal SECDED 5 ns area | +36.7211375791% |
| Temporal SECDED 5 ns timing | +68.6296531578% |
| Temporal SECDED 5 ns energy/op | −19.3366059827% |
| Structural Hsiao 10 ns area | −0.5641215486% |
| Structural Hsiao 10 ns timing | +2.6556507609% |
| Structural Hsiao 10 ns energy/op | +1.3283946898% |
| SECDED 10 ns internal power | +6.7723518051% |
| SECDED 10 ns switching power | −49.4813317116% |
| SECDED 10 ns leakage power | +34.4267937955% |
| SECDED 10 ns total power | −23.4190052226% |

These are descriptive means over the prospectively matched deterministic seeds,
not population estimates. The mechanism claim remains limited: switching is
the largest absolute top-level contributor to the energy difference, but the
current evidence does not prove glitch suppression.
