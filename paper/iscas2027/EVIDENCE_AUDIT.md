# ISCAS 2027 Evidence Audit

## Audit boundary

This audit was initiated before manuscript prose or numerical claims were drafted.
It records the repository state inspected on 2026-09-10 and applies the admission
rule `correctness -> reliability requirement -> setup and hold feasibility ->
measured implementation cost -> activity energy -> lifecycle analysis`. A result
may be useful at one boundary while remaining ineligible at another.

- Working branch: `codex/green-v33-activity-complete-e5`.
- Working commit: `34df5bf0d212c341ba1df61fcee67471cc277b9a`.
- Worktree: dirty before this paper directory was created. Existing modified and
  untracked campaign, executable, test-fixture, PDF, and temporary-render files
  are user-owned and are not changed by this paper build.
- Protected DATE foundation: final Revision-3 paper commit
  `9968f9b15f949d38faf944a3546ea736cfab63df`; qualified physical foundation
  `b51291442bbd04346dac939dea6ba7d532b9c5c4`.
- Latest evidence-aware GREEN Matrix: v3.3 additive E5 campaign, based on v3.2
  commit `29f20b196e04c713f88fd1a93440a2ff47986f06` and matched physical campaign
  commit `daaa83b6b3571060aec9d4d753b4907df5a2ba47`.

## Evidence-tier semantics

| Tier | Repository definition | Use in this paper |
|---|---|---|
| E0 | Absent; blocking reason required | Missing values remain missing |
| E1 | Assumed or exploratory parametric input | Scenario-only, never measured |
| E2 | Published literature or external model in its native boundary | Method or scenario support |
| E3 | Analytical, exact logical enumeration, or RTL-derived result | Code/RTL behavior only |
| E4 | Synthesis or place-and-route tool estimate | Physical implementation evidence |
| E5 | Activity-qualified, matched post-route result | ECC-logic operation energy |
| E6 | Independently cross-validated characterization | None admitted |
| E7 | Silicon or manufacturing measurement | None admitted |

Tier order is not a global quality score. Boundary, PVT, technology, workload,
implementation identity, and qualification status remain part of every claim.

## Quantity and claim audit

| Quantity / Claim | Architecture | Condition | Evidence source | Status | Can appear numerically in paper? |
|---|---|---|---|---|---|
| Payload/stored width, latency, II | U0 | 64/64, 1 cycle, II=1 | `green_v3_2_matched_openram_orfs_validation/ARCHITECTURE_AUDIT.json` | QUALIFIED IDENTITY | Yes |
| Payload/stored width, latency, II | SECDED | 64/72, 1 cycle, II=1 | same architecture audit | QUALIFIED IDENTITY | Yes |
| Payload/stored width, latency, II | HSIAO_SECDED | 64/72, 1 cycle, II=1 | same architecture audit | QUALIFIED IDENTITY | Yes |
| Payload/stored width, latency, II | BCH_78_64_T2 | 64/78 logical bits, 1 cycle, II=1; implemented with two physical padding bits | same architecture audit | QUALIFIED IDENTITY | Yes, with padding note |
| No-error SRAM-model round trip | U0 | Four deterministic payloads | `FUNCTIONAL_VALIDATION_U0.json` and summary | REGRESSION_VALIDATED | Yes, as a finite regression |
| W1 correction and W2 detection | SECDED | All masks over four payloads; frozen exact evidence supplies unrestricted code result | `FUNCTIONAL_VALIDATION_SECDED.json`; architecture audit | E3 QUALIFIED AT STATED BOUNDARIES | Yes |
| W1 correction and W2 detection | HSIAO_SECDED | All masks over four payloads; frozen exact logical implementation evidence | `FUNCTIONAL_VALIDATION_HSIAO_SECDED.json`; architecture audit | E3 QUALIFIED AT STATED BOUNDARIES | Yes |
| W1 and W2 correction | BCH_78_64_T2 | All declared W1/W2 masks over four payloads; 3,082 fixed-mask symbolic-payload proofs inherited | `FUNCTIONAL_VALIDATION_BCH_78_64_T2.json`; architecture audit | E3 QUALIFIED FOR NAMED RTL | Yes |
| Adjacent-double correction | SEC_DAEC | Counterexample at payload-adjacent bits 4 and 5 | `FUNCTIONAL_VALIDATION_SEC_DAEC.json`; architecture audit | FAILED / EXCLUDED | Only as exclusion |
| Interleaving benefit | I1/I2 proposals | No RTL and no physical-to-logical bit map | `BIT_MAPPING_AUDIT.json`; `INTERLEAVER_ROUTED_VALIDATION.json` | BLOCKED | No numerical benefit |
| Route and GDS completion | U0, SECDED, HSIAO_SECDED, BCH_78_64_T2 | 10 and 5 ns; seeds 11,13,17,19,23 | `PHYSICAL_RUN_RESULTS.csv` | 40/40 ROUTED, 40/40 GDS, 0 route DRC errors | Yes |
| Setup feasibility | U0 | 10 ns and 5 ns | `TIMING_FEASIBILITY.json` | 5/5 at each target | Yes |
| Setup feasibility | SECDED | 10 ns / 5 ns | same | 5/5 / 0/5 | Yes |
| Setup feasibility | HSIAO_SECDED | 10 ns / 5 ns | same | 5/5 / 0/5 | Yes |
| Setup feasibility | BCH_78_64_T2 | 10 ns / 5 ns | same | 0/5 / 0/5 | Yes, as a boundary |
| Hold feasibility | U0 | 10 ns | `PHYSICAL_RUN_RESULTS.csv` | 5/5 | Yes |
| Hold feasibility | SECDED | 10 ns | same | 5/5 | Yes |
| Hold feasibility | HSIAO_SECDED | 10 ns | same | 4/5; seed 11 WNS = -0.0137477 ns | Yes; primary cohort excludes seed 11 |
| Hold feasibility | BCH_78_64_T2 | 10 ns | same | 5/5 hold, but 0/5 setup | Yes, only alongside setup failure |
| Full setup-and-hold-clean matched SECDED/Hsiao pairs | SECDED, HSIAO_SECDED | 10 ns; seeds 13,17,19,23 | derived directly from `PHYSICAL_RUN_RESULTS.csv` | 4 MATCHED PAIRS | Yes; primary comparison |
| Standard-cell area | all four included identities | 10 ns; five seeds | `SEED_STATISTICS.csv` | E4 TOOL ESTIMATE | Yes, with macro boundary stated |
| Wirelength and via count | all four included identities | 10 ns; five seeds | `SEED_STATISTICS.csv`; `E5_MATCHED_SEED_DELTAS.csv` | E4 TOOL ESTIMATE | Yes, descriptive |
| Vectorless power | all four included identities | 10 ns and 5 ns | `PHYSICAL_RUN_RESULTS.csv`; `SEED_STATISTICS.csv` | E4 DIAGNOSTIC | Yes only as vectorless diagnostic; not energy |
| Operation-normalized ECC-logic energy | SECDED, HSIAO_SECDED | 10 ns; 16 warm-up cycles; 256 measured operations; five operation classes | `RUN_MANIFEST.json`; `GREEN_V3_3_ADDITIVE_MATRIX.json` | 46 E5 RECORDS AT CAMPAIGN SETUP-ONLY GATE | Yes, but primary paper cohort is the 40 records from four setup-and-hold-clean seed pairs |
| Clean-read/correction/detection sensitivity records | SECDED, HSIAO_SECDED | 10 ns; seed 11 | same plus `PHYSICAL_RUN_RESULTS.csv` | E5 ACTIVITY-QUALIFIED, HOLD-INCOMPLETE PAIR | Yes only as labeled sensitivity |
| Idle/write seed-11 energy | SECDED, HSIAO_SECDED | 10 ns | `FAILED_PARTIAL_EXPERIMENTS.json` | BLOCKED: X-state activity incomplete | No |
| Activity boundary | SECDED, HSIAO_SECDED | final routed gate netlist, zero-delay VCD, final SPEF | `RUN_MANIFEST.json` | QUALIFIED FOR DECLARED E5 LOGIC BOUNDARY | Yes |
| Activity coverage | SECDED, HSIAO_SECDED | 72/72 macro-output roots; functional logic 99.298390-99.356061%; sequential 100% | `CAMPAIGN_STATUS.json`; `RUN_MANIFEST.json` | QUALIFIED | Yes |
| Whole-memory operation energy | all | address/data/state-dependent macro-internal energy absent or partial | `SRAM_MACRO_POWER_QUALIFICATION.json`; `SRAM_MACRO_POWER_AUDIT.md` | NOT_QUALIFIED | No |
| U0 activity energy | U0 | Any operation class | v3.3 campaign status/workload manifest | NOT RUN / E5 BLOCKED | No |
| BCH activity energy | BCH_78_64_T2 | Any operation class | v3.3 campaign status; timing diagnosis | NOT RUN; TIMING-INELIGIBLE | No |
| Fresh 256x72 OpenRAM macro | candidate SRAM | OpenRAM 1.2.48, SKY130A, TT/1.8 V/25 C | `OPENRAM_PROVENANCE.json` | TIMEOUT after partial generation; DRC/LVS/characterization not completed | Geometry only as failed-attempt record, not as a macro result |
| Inherited SRAM views | U0/SECDED/Hsiao/BCH wrappers | SRAM22 256x64m4w8 and 256x8m8w1, tt/25 C/1.80 V | `OPENRAM_MACRO_MANIFEST.json`; macro power audit | INHERITED; LEF/GDS/Liberty/Verilog present; independent DRC/LVS and full power not established | Only provenance/status and interface use; no fresh-macro or signoff claim |
| Physical bitcell-to-codeword topology | all | inherited macro views | `BIT_MAPPING_AUDIT.json` | BLOCKED | No |
| Qcrit | all | SKY130/SRAM22 | v3.3 campaign status | BLOCKED | No |
| Physical SER/FIT/SDC/DUE | all | field or beam environment | v3.2/v3.3 claim maps | BLOCKED | No |
| Conditional logical response | U0/E0 legacy logical population | enumerated logical mask classes only | `green_matrix_v3_2/data/CONDITIONAL_RELIABILITY.json` | CONDITIONAL E3; no event probability | Only if clearly labeled; not needed for headline results |
| Particle-beam reliability | all | none | repository absence audit | UNAVAILABLE | No |
| SKY130 manufacturing carbon | all | cradle-to-fab/gate candidate | `MANUFACTURING_CARBON_MODEL.md`; `SOURCE_REGISTRY.json` | BLOCKED: no matched inventory | No absolute value |
| Operational carbon relation | SECDED/Hsiao | declared workload, operation count, and grid intensity | v3 methodology; E5 energy | PARAMETRIC, DIMENSIONALLY VALID | Equation/threshold only; no assumed grid number in headline claims |
| Lifecycle carbon | all | manufacturing + use phase | `CSCI_MATHEMATICAL_AUDIT.md`; evidence matrix | BLOCKED | No absolute value or ranking |
| Carbon break-even condition | SECDED/Hsiao | symbolic embodied-carbon delta; measured logic-energy delta | derived from qualified E5 and dimensional audit | CONDITIONAL ANALYTICAL | Yes, symbolically |
| Global GREEN winner | all | current qualified evidence | v3.3 campaign status | `NO_GLOBAL_WINNER_QUALIFIED` | Yes, as a qualification result |
| Technology portability | all | one SKY130HD/SRAM22/open-source flow condition | campaign manifests | NOT_ASSESSABLE | No |
| Silicon measurement | all | none | repository audit | UNAVAILABLE | No |

## Campaign and failure inventory

The frozen sequence inspected is: DATE Revision-3 foundation; GREEN v3.0
imec-public-evidence-aligned methodology; GREEN v3.1 physical population;
GREEN v3.2 evidence-aware decision model; GREEN v3.2 matched OpenRAM/ORFS
validation; and GREEN v3.3 activity-complete E5. Historical v2 normalized-score
and NSGA-II artifacts remain provenance records, not the decision engine for this
paper.

Preserved negative results include the failed SEC-DAEC adjacent mask, ten initial
Hsiao synthesis failures caused by the memory-inference guard, the 256x72 OpenRAM
runtime cutoff, v3.3 activity-remediation attempts, unavailable seed-11 idle/write
traces, the Hsiao seed-11 hold violation, and all BCH setup failures. None is
replaced or imputed.

## Admission decision

The paper admits U0, conventional SECDED, Hsiao SECDED, and the named BCH
implementation as the physical experiment population. U0 is a baseline, not an
ECC. The equal-service, activity-energy comparison contains only conventional
SECDED and Hsiao SECDED. The primary comparison uses matched seeds 13, 17, 19,
and 23 because those pairs are setup- and hold-clean. BCH remains a routed
stronger-correction feasibility boundary. No architecture receives a qualified
whole-memory, physical failure-rate, or absolute lifecycle-carbon value.

