# Gate 03F Stage 1B — Starting-Boundary Reconciliation and Environment Recovery

Date: 2026-08-24

Scope: read-only environment recovery, provenance reconstruction, and experimental-boundary adjudication. No OpenROAD/ORFS physical run, container pull, package change, protocol freeze, Gate 04 confirmatory experiment, commit, or push was performed.

## 1. WSL/environment recovery status

Status: **RECOVERY BLOCKED WITHOUT AUTHORIZED ENVIRONMENT CHANGE**.

The installed service inventory returned one WSL-specific service:

| Service name | Display name | State | Start type |
| --- | --- | --- | --- |
| `WSLService` | WSL Service | Running | Automatic |

No `vmcompute`, `HNS`, or legacy `LxssManager` service was present in the service inventory returned to this session. Ubuntu `24.04` remains registered as a stopped WSL2 distribution.

`wsl.exe --status` reports that WSL2 cannot start because virtualization is not enabled or the Virtual Machine Platform is unavailable. A direct attempt to enter `Ubuntu-24.04` fails before Linux starts with:

```text
Wsl/Service/CreateInstance/CreateVm/HCS/HCS_E_SERVICE_NOT_AVAILABLE
The operation could not be started because a required feature is not installed.
```

The one permitted minimal recovery action was attempted: restart the existing `WSLService`. The service manager denied the stop operation (`Cannot open 'WSLService' service on computer '.'`), the service remained running, and the subsequent WSL start produced the same HCS error.

An elevated query of the Windows optional-feature state was not available to this session. Consequently, the evidence does not distinguish conclusively between a disabled `VirtualMachinePlatform` feature, a disabled hypervisor boot/firmware setting, or another unavailable HCS dependency. Fixing any of those may require an elevated feature or boot configuration change. Stage 1B does not authorize making that change, upgrading/reinstalling WSL, or modifying the scientific Linux environment.

Required recovery before continuation:

1. inspect `VirtualMachinePlatform`, `Microsoft-Windows-Subsystem-Linux`, hypervisor boot state, and firmware virtualization from an elevated host session;
2. restore the previously installed WSL2 capability without upgrading WSL, changing Ubuntu packages, or recreating the distribution;
3. demonstrate a read-only command inside the existing `Ubuntu-24.04` distribution.

## 2. External evidence integrity

Status: **UNRESOLVED — EXTERNAL TREES INACCESSIBLE**.

The following expected Linux-side paths could not be inspected:

```text
/var/lib/green-ecc-gate03e
/var/lib/green-ecc-gate03er
/var/lib/green-ecc-gate03es
/opt/OpenROAD-flow-scripts
/var/lib/green-ecc-gate04
```

Repository manifests continue to record the following historical identities, but Stage 1B could not revalidate them against the external bytes:

| Identity | Recorded value | Stage 1B verification |
| --- | --- | --- |
| ORFS image | `openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e` | UNRESOLVED |
| ORFS source commit | `56496f3980fb6e9e58f10c8aea4a98949c0fe5f2` | UNRESOLVED |
| OpenROAD revision cited by producer adjudication | `ab6fd26351dc449e69059684dc6aa9ae9046eb36` | UNRESOLVED |
| SKY130 timing view | `sky130_fd_sc_hd__tt_025C_1v80` | UNRESOLVED |
| Gate 03E runs | `gcd-run-01`, `gcd-run-02` | UNRESOLVED |
| Gate 03E-R runs | `gcd-run-03`, `gcd-run-04` | UNRESOLVED |
| Gate 03E-S runs | `gcd-run-05`, `gcd-run-06` | UNRESOLVED |

The repository-side run inventories, comparisons, and SHA-256 indexes were not treated as substitutes for the external artifacts they identify. Runs 1–6 therefore remain historically documented but not freshly integrity-verified.

## 3. Gate 04 historical execution inventory

Status: **PARTIAL LOCAL RECONSTRUCTION; EXTERNAL COMPLETENESS UNRESOLVED**.

The checked-in/untracked `FLOW_RUN_MATRIX.csv` contains 60 rows and still marks all rows `PLANNED`. It is a result-blind plan, not a reliable execution ledger. Four local policy-amendment documents establish that physical work nevertheless began.

| Run or attempt | Launch | Synthesis | Placement | CTS | Routing | Extraction/final artifacts | Equivalence | Power | Local evidence basis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `secded-comb-10ns-seed11-attempt1` | YES | NO | NO | NO | NO | NO | NO | NO | Amendment 01 says it failed before synthesis while deriving `ABC_CLOCK_PERIOD_IN_PS`. |
| `secded-comb-10ns-seed11-attempt2` | YES | YES | YES | YES | YES | YES | YES, completed additively | YES, three activity cases completed additively | Amendments 02 and 03 say the official RTL-to-GDS flow completed and the preserved artifacts later passed two-leg equivalence and activity-power analysis. |
| `secded-comb-10ns-seed29-attempt1` | YES | YES | YES | YES | YES | YES | YES | YES | Amendment 04 says the flow, equivalence, and all frozen activity-power cases completed before a Python validator false positive. |
| Other planned rows or additional retries | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | The external `/var/lib/green-ecc-gate04` execution tree is inaccessible. |

The executed jobs influenced implementation/debugging policy:

- Amendment 01 changed runner invocation after observing the attempt-1 pre-synthesis failure.
- Amendment 02 changed the generic-cell predicate after inspecting the completed attempt-2 netlist.
- Amendment 03 replaced the equivalence proof schedule after prior proof attempts did not terminate.
- Amendment 04 changed a Python regular expression after the seed-29 validator false positive.

The amendment documents state that RTL, physical artifacts, SDC, seeds, traces, scientific hypotheses, materiality thresholds, and selection rules did not change. This claim cannot be independently confirmed until the external policy bundles, run metadata, raw manifests, logs, and results are readable.

All physical Gate 04 attempts that predate the Gate 03F frozen measurement contract are classified:

```text
PRE_GATE03F_EXPLORATORY
```

They must be preserved and may be used only for debugging, provenance reconstruction, and identifying validation defects.

## 4. Confirmatory-vs-exploratory boundary

The following boundary is mandatory:

> Confirmatory Gate 04 data may be generated only after the Gate 03F measurement contract, metric definitions, activity methodology, seed policy, validity criteria, and stability rules have been frozen.

Existing `PRE_GATE03F_EXPLORATORY` runs:

- must not be deleted, overwritten, renamed, or relabeled as confirmatory;
- must retain their original attempt IDs, policies, amendments, logs, and raw hashes;
- must not be used to select Gate 03F numerical tolerances, stability limits, outlier rules, clocks, seeds, designs, or effect-separation thresholds;
- may be used to debug runners, metric extraction, source provenance, equivalence tooling, and fail-closed validation;
- must remain outside the future confirmatory Gate 04 statistical dataset.

The future confirmatory run-root namespace must be distinct and created only after Gate 03F authorization. No such namespace is authorized by this report.

## 5. Verified seed behavior

Status: **UNRESOLVED FROM PINNED SOURCE**.

Local Gate 04 files claim that the pinned flow recognizes:

```text
GPL_RANDOM_SEED
GRT_SEED
OR_SEED
```

and locally assign all three to a matrix seed. The local freeze script was designed to copy and grep relevant pinned ORFS source files. Those claims do not satisfy Stage 1B because `/opt/OpenROAD-flow-scripts` and any external `SEED_CONTROL_SOURCE_PROOF` are inaccessible.

The historical Gate 03E/03E-R/03E-S command manifests do not explicitly export these three variables. Therefore:

| Question | Finding |
| --- | --- |
| Where `GPL_RANDOM_SEED` is consumed | UNRESOLVED |
| Where `GRT_SEED` is consumed | UNRESOLVED |
| Where `OR_SEED` is consumed | UNRESOLVED |
| Defaults in the pinned source | UNRESOLVED |
| Runs 1–6 effective seed values | UNRESOLVED; only an implicit/default behavior is evidenced locally |
| Synthesis stochastic control | UNRESOLVED |
| CTS stochastic control | UNRESOLVED |

No seed was changed.

## 6. Historical GCD metric eligibility

Eligibility requires the external artifact, producer, configuration, seed interpretation, and metric definition to be verified together. Repository comparisons alone show strong historical repeatability, but current external integrity and source verification are missing.

Historical Gate 03E power is classified `INELIGIBLE` because it was not generated using a frozen DATE-quality activity-based methodology with a defined useful-operation rate. This classification does not depend on external recovery.

| Historical run | Area | Timing | Physical topology | Power | Reason |
| --- | --- | --- | --- | --- | --- |
| `gcd-run-01` | UNRESOLVED | UNRESOLVED | UNRESOLVED | INELIGIBLE | External bytes and seed defaults cannot be verified; historical power methodology does not match the planned activity-based definition. |
| `gcd-run-02` | UNRESOLVED | UNRESOLVED | UNRESOLVED | INELIGIBLE | Same as run 1. |
| `gcd-run-03` | UNRESOLVED | UNRESOLVED | UNRESOLVED | INELIGIBLE | Repository evidence says semantic artifacts and QoR passed, but external bytes, producer source, and seed defaults remain inaccessible. |
| `gcd-run-04` | UNRESOLVED | UNRESOLVED | UNRESOLVED | INELIGIBLE | Same as run 3. |
| `gcd-run-05` | UNRESOLVED | UNRESOLVED | UNRESOLVED | INELIGIBLE | Repository evidence records raw ODB identity, complete semantic equality, and zero QoR deltas; external bytes and seed defaults remain unverified. |
| `gcd-run-06` | UNRESOLVED | UNRESOLVED | UNRESOLVED | INELIGIBLE | Same as run 5. |

If external recovery succeeds, area, timing, topology, and routing eligibility must be adjudicated separately. A passing area decision must not automatically admit power or energy.

## 7. Proposed DATE power methodology

No power analysis was run during Stage 1B. The historical control power fields are insufficient for a DATE claim.

A defensible protocol must freeze all of the following before prospective runs:

1. **Physical analysis point:** final post-route netlist/ODB, extracted parasitics, final SDC, and the exact pinned OpenSTA/OpenROAD producer.
2. **Operating condition:** exact Liberty corner, temperature, voltage, parasitic corner, clock period, and timing-validity requirement. The recorded candidate is SKY130HD TT, 25 °C, 1.8 V, subject to external verification.
3. **Useful operation:** one explicitly defined ECC transaction and the point at which its result becomes useful. Encoding, decoding, checking, fault injection, and boundary/reference activity must not be silently mixed.
4. **Activity source:** a deterministic, architecture-neutral trace generated from a frozen workload specification. No random payload distribution, fault distribution, warm-up length, or measured-operation count may be invented after results are visible.
5. **Clock activity:** explicit clock waveform, duty cycle, frequency, reset interval, clock-gating policy, and pipeline fill/drain treatment.
6. **Input annotation:** direct VCD/SAIF annotation counts, unannotated inputs/pins, and the exact name/scope mapping must be retained. Activity propagation must be reported separately from direct annotation.
7. **Power components:** internal, switching, leakage, and total power must be retained with producer units and source fields. Tool-estimated power must not be described as silicon measurement.
8. **Throughput and latency:** useful steady-state throughput in operations per second and boundary-to-boundary latency must both be reported. A pipeline may have multi-cycle latency while sustaining one useful operation per cycle after filling; these concepts must not be conflated.
9. **Energy per useful operation:** derive as

   ```text
   energy_per_useful_operation = average_total_power / useful_operation_throughput
   ```

   only over the frozen measurement interval and only when timing validity, operation count, pipeline fill/drain treatment, and activity annotation pass. `power × arbitrary time` is prohibited.
10. **Repeatability:** the same activity trace and analysis script must be applied to every qualifying control and ECC repetition. Power stability must be measured under that final methodology, not inferred from historical vectorless/default power fields.

The existing deterministic Gate 04 trace proposal may be inspected as exploratory debugging evidence after WSL recovery, but it cannot be adopted merely because exploratory results already exist. Its workload and operation semantics require an independent, result-blind justification before protocol freeze.

## 8. Revised minimum run matrix

No historical GCD repetition presently satisfies the complete planned methodology. The preferred upper-bound matrix therefore remains the minimum defensible prospective plan:

| Design | Repetitions | Seed relationship | Purpose |
| --- | ---: | --- | --- |
| GCD control | 5 | same explicitly verified seed | area, timing, topology, routing, activity-based power, and energy-method stability |
| SECDED representative | 3 | same explicitly verified seed and rules | representative moderate ECC stability |
| BCH `(78,64,t=2)` | 3 | same explicitly verified seed and rules | representative complex ECC stability |
| **Total** | **11** | — | — |

No reduction is justified during Stage 1B. After external recovery, historical GCD runs may reduce only the area/timing/topology evidence requirement if they become `ELIGIBLE`; they cannot replace five power controls unless power is recomputed under the final frozen methodology with preserved independent outputs and the complete control-repetition requirement remains scientifically satisfied.

No run in this matrix was launched.

## 9. Remaining blockers

1. WSL2 cannot create its VM because the virtualization/HCS platform is unavailable.
2. The Windows optional-feature and hypervisor state has not been inspected from an elevated host session.
3. External Gate 03E/03E-R/03E-S artifact trees cannot be rehashed.
4. Runs 1–6, the pinned ORFS checkout, container identity, platform collateral, and source/config bytes cannot be freshly verified.
5. The external Gate 04 run inventory is inaccessible, so the local three-attempt reconstruction is not complete.
6. Actual seed consumption/defaults cannot be verified from pinned ORFS/OpenROAD source.
7. Historical GCD area, timing, routing, and topology eligibility remains unresolved.
8. A result-blind DATE activity and useful-operation specification has not been frozen.
9. The worktree contains uncommitted Gate 03E-R, Gate 03E-S, and Gate 04 evidence plus compatibility edits; their preservation boundary must remain explicit.

Repository validation after creating this additive report produced:

- `make`: PASS;
- `make test`: FAIL with 427 passed and 2 failed;
- `python3 -m pytest -q`: FAIL with 429 passed and 2 failed.

Both failures are closed-scope rejections of `docs/date2027/rigour_gate_03f/GATE_03F_STAGE1B_BOUNDARY_RECONCILIATION.md`: `test_gate01_gate02_immutable_authorized_scope_and_binary_verdict` and `test_gate03e_artifact_validator`. No functional, build, or scientific test failed. The historical validators were preserved rather than weakened during this boundary-only stage.

## 10. Recommendation

Do not freeze the Gate 03F protocol and do not authorize any confirmatory physical run.

First restore the existing WSL2 capability without version/package changes. Then perform, in order:

1. raw manifest verification of every external Gate 03E/03E-R/03E-S tree;
2. complete external Gate 04 attempt inventory and classification as `PRE_GATE03F_EXPLORATORY`;
3. pinned-source seed tracing with file/line evidence;
4. metric-by-metric historical GCD eligibility adjudication;
5. result-blind activity, throughput, latency, and energy-method definition.

Only after those items pass should the formal Gate 03F protocol be frozen.

NOT_READY_TO_FREEZE_GATE03F_PROTOCOL
