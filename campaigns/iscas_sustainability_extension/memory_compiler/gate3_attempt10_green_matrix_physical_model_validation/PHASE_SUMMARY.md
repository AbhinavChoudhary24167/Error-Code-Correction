# Attempt10 phase completion report

This report is generated from `CAMPAIGN_STATUS.json`. It preserves explicit evidence limits and does not promote missing measurements.

## Phase A: Liberty output-transition model sensitivity

| Required item | Result |
|---|---|
| 1. Exact classification | STRICT_MATRIX_EXECUTED_WITH_DETERMINISTIC_U0_RSZ0090_ABORTS |
| 2. Proven | All six frozen SRAM22 Liberty views and 24 output transition tables were audited.; The global 0.04 ns value conflicts with every supplied output transition table.; All 30 strict configurations were executed; 20 completed and 10 diagnostic U0 runs aborted deterministically at RSZ-0090.; Corrected and no-global E0 PPA are identical across all five seeds. |
| 3. Unproven | Foundry accuracy of either diagnostic view.; Corrected/counterfactual U0 PPA because strict runs abort before completion. |
| 4. Original vs corrected | UPSTREAM_ORIGINAL is retained as production evidence; isolated research-corrected and no-global views are sensitivity-only. |
| 5. U0/E0 matched results | Original U0/E0 reproduce Attempt09 for five seeds. Diagnostic E0 completes; diagnostic U0 aborts before PPA. |
| 6. Five-seed robustness | Original 10/10 and diagnostic E0 10/10 complete; diagnostic U0 10/10 aborts (strict plus retained non-qualifying continuation evidence). |
| 7. PPA effect | For E0, corrected versus original means: standard-cell area -6.7524%, wirelength +0.7381%, vias -7.5332%, tool power -0.5083%; U0 is not qualified. |
| 8. Energy effect | No activity-qualified energy conclusion; only post-route tool-power sensitivity. |
| 9. Reliability effect | No reliability effect measured. |
| 10. Carbon effect | No qualified carbon effect. |
| 11. GREEN ranking effect | No ranking is permitted while source objectives are unqualified. |
| 12. ISCAS impact | Supports a physically observed optimizer sensitivity claim for E0 and a deterministic feasibility-boundary claim for U0. |
| 13. Unsupported claims | Foundry-corrected Liberty; Diagnostic U0 PPA equivalence; Gate-3 closure |
| 14. Repository/integrity | PASS: baseline and final repository/external checkpoints, Attempts 1-9, protected DATE evidence, and frozen SRAM22 sources all verify. |
| 15. Recommended next action | Independently re-characterize SRAM output constraints and investigate U0 RSZ-0090 without changing Gate-3 limits. |

## Phase B: 256x64 data-rstb physical characterization

| Required item | Result |
|---|---|
| 1. Exact classification | INSUFFICIENT_EVIDENCE |
| 2. Proven | The 256x64 rise capacitance is 0.448008 pF versus 0.250926 pF for 256x8 (1.785419x).; Macro pin load dominates measured routed wire capacitance.; Zero-wire and localized strongest-driver tests still miss 0.351 ns for the 256x64 macro; the 256x8 comparison can pass.; OpenSTA and table interpolation agree within 4.34e-8 ns. |
| 3. Unproven | A universal frozen-interface impossibility proof.; That the 0.351 ns input limit is invalid. |
| 4. Original vs corrected | This phase retains upstream input constraints and does not use the output-transition diagnostic correction. |
| 5. U0/E0 matched results | Attempt09 seed11 is reproduced: U0 0.619147718 ns, E0 data 0.615635812 ns, E0 ECC 0.307288498 ns. |
| 6. Five-seed robustness | Five-seed historical closure remains 5/5 setup/hold and 0/5 external-DRV clean; controlled diagnostics are characterization experiments. |
| 7. PPA effect | No retained implementation PPA replacement. |
| 8. Energy effect | No energy result. |
| 9. Reliability effect | Explains a physical parameter relevant to fault-protection implementation but changes no reliability rate. |
| 10. Carbon effect | No carbon result. |
| 11. GREEN ranking effect | No ranking effect. |
| 12. ISCAS impact | Supports the narrower-macro load explanation while preserving an explicit evidence limit. |
| 13. Unsupported claims | Frozen interface impossibility; Constraint provenance inconsistency |
| 14. Repository/integrity | PASS: baseline and final repository/external checkpoints, Attempts 1-9, protected DATE evidence, and frozen SRAM22 sources all verify. |
| 15. Recommended next action | Obtain independent macro input-slew characterization including internal RC/transient evidence. |

## Phase C: Physical GREEN matrix schema

| Required item | Result |
|---|---|
| 1. Exact classification | SCHEMA_COMPLETE_WITH_EXPLICIT_MISSINGNESS |
| 2. Proven | The required physical, reliability, energy, carbon, and score fields have typed semantics and explicit sentinel values.; The physical table contains 20 provenance-linked rows. |
| 3. Unproven | Missing quantities are not measurements. |
| 4. Original vs corrected | Rows explicitly label original or research-corrected Liberty. |
| 5. U0/E0 matched results | U0/E0 rows remain separate by architecture, model, and seed. |
| 6. Five-seed robustness | Five canonical seeds are represented for each baseline/model combination that can be populated. |
| 7. PPA effect | Measured physical fields are preserved without imputation. |
| 8. Energy effect | Unqualified energy stays NOT_QUALIFIED. |
| 9. Reliability effect | Physical rates stay NOT_QUALIFIED. |
| 10. Carbon effect | Carbon stays NOT_QUALIFIED. |
| 11. GREEN ranking effect | No scores are computed. |
| 12. ISCAS impact | Provides the auditable data contract for later ISCAS evaluation. |
| 13. Unsupported claims | None added. |
| 14. Repository/integrity | PASS: baseline and final repository/external checkpoints, Attempts 1-9, protected DATE evidence, and frozen SRAM22 sources all verify. |
| 15. Recommended next action | Populate currently missing fields only from traceable experiments. |

## Phase D: U0/E0 matched GREEN baseline

| Required item | Result |
|---|---|
| 1. Exact classification | PROVENANCE_AWARE_PHYSICAL_BASELINE_POPULATED |
| 2. Proven | Original five-seed U0/E0 metrics and completed corrected E0 metrics are populated.; Diagnostic U0 abort rows retain explicit NOT_MEASURED values. |
| 3. Unproven | Corrected U0 physical comparison.; Gate-3 pass. |
| 4. Original vs corrected | Both baselines coexist; no silent substitution. |
| 5. U0/E0 matched results | Ten upstream-original rows plus ten research-corrected rows are represented. |
| 6. Five-seed robustness | Original five seeds complete for both; corrected E0 five seeds complete; corrected U0 five runs abort. |
| 7. PPA effect | E0 material changes are quantified; U0 diagnostic change is unqualified. |
| 8. Energy effect | Energy fields remain gated. |
| 9. Reliability effect | Reliability fields remain gated. |
| 10. Carbon effect | Carbon fields remain gated. |
| 11. GREEN ranking effect | Rows are excluded from ranking while required objectives remain unavailable. |
| 12. ISCAS impact | Provides a defensible matched physical baseline. |
| 13. Unsupported claims | Macro-internal DRC; Independent LVS; Qualified energy |
| 14. Repository/integrity | PASS: baseline and final repository/external checkpoints, Attempts 1-9, protected DATE evidence, and frozen SRAM22 sources all verify. |
| 15. Recommended next action | Close the corrected U0 feasibility gap or retain it as an excluded design point. |

## Phase E: Activity-qualified energy

| Required item | Result |
|---|---|
| 1. Exact classification | RTL_ACTIVITY_COMPLETE_ENERGY_NOT_QUALIFIED |
| 2. Proven | Eight workloads execute identically for U0 and E0 with checked outputs and no unknowns.; A seed-11 upstream-original post-route diagnostic records exact annotation coverage and power-component tool estimates. |
| 3. Unproven | Activity-qualified energy/access.; Five-seed and corrected-model activity power.; Validated macro read/write internal energy.; Glitch-aware gate activity and disjoint component attribution. |
| 4. Original vs corrected | Activity traces do not change Liberty; sensitivity models were not used for the post-route diagnostic. |
| 5. U0/E0 matched results | Workload traces are matched; post-route coverage is U0 48.68% and E0 4.35%. |
| 6. Five-seed robustness | RTL activity is deterministic, but post-route activity power is only seed11. |
| 7. PPA effect | No physical implementation changes were made in this phase. |
| 8. Energy effect | Energy values remain NOT_QUALIFIED. |
| 9. Reliability effect | No rate effect. |
| 10. Carbon effect | No carbon values may consume the partial estimate. |
| 11. GREEN ranking effect | No GREEN score may consume the partial estimate. |
| 12. ISCAS impact | Defines a reproducible workload-to-activity chain and documents why power-to-energy remains incomplete. |
| 13. Unsupported claims | Energy per access; Architecture energy advantage; Macro power-model accuracy |
| 14. Repository/integrity | PASS: baseline and final repository/external checkpoints, Attempts 1-9, protected DATE evidence, and frozen SRAM22 sources all verify. |
| 15. Recommended next action | Run mapped, glitch-aware, five-seed activity with independently validated macro power and explicit component partitioning. |

## Phase F: Physical bit interleaving

| Required item | Result |
|---|---|
| 1. Exact classification | PHYSICAL_TOPOLOGY_MAPPING_INCOMPLETE |
| 2. Proven | I0 macro placements and macro dimensions are extracted from frozen DEF/LEF evidence.; I1/I2 are explicit banking and transpose proposals with stated implementation requirements. |
| 3. Unproven | Bitcell coordinates or address-to-physical-bit maps.; Physical separation, routing, area, energy, and latency for I1/I2. |
| 4. Original vs corrected | Independent of Liberty model. |
| 5. U0/E0 matched results | Both architectures are described, but only I0 macro-level organization has physical evidence. |
| 6. Five-seed robustness | Five-seed placement evidence exists for I0; proposals are not implemented. |
| 7. PPA effect | I1/I2 PPA is NOT_MEASURED. |
| 8. Energy effect | I1/I2 energy is NOT_MEASURED. |
| 9. Reliability effect | No physical interleaving coverage claim. |
| 10. Carbon effect | No qualified carbon result. |
| 11. GREEN ranking effect | No ranking effect. |
| 12. ISCAS impact | Defines implementable experiments without treating a logical permutation as physical evidence. |
| 13. Unsupported claims | Physical interleaving effectiveness; Interleaving overhead |
| 14. Repository/integrity | PASS: baseline and final repository/external checkpoints, Attempts 1-9, protected DATE evidence, and frozen SRAM22 sources all verify. |
| 15. Recommended next action | Implement I1/I2 banking/controller changes and extract address-to-physical mapping. |

## Phase G: Reliability GREEN matrix

| Required item | Result |
|---|---|
| 1. Exact classification | PHYSICAL_RELIABILITY_RATES_NOT_QUALIFIED |
| 2. Proven | Logical controls show E0 corrects all 72 SBU positions and detects all 2556 DBU pairs in the enumerated codeword model.; Three-bit logical patterns expose possible miscorrection/SDC and are not mislabeled as physical MBU rates. |
| 3. Unproven | Physical SER, FIT, SDC, DUE, burst, and interleaving coverage rates. |
| 4. Original vs corrected | Independent of Liberty model until physical/topology coupling is available. |
| 5. U0/E0 matched results | U0/E0 logical controls exist; physical comparison is withheld. |
| 6. Five-seed robustness | Deterministic logical enumeration is complete; physical event sampling is empty. |
| 7. PPA effect | No PPA effect. |
| 8. Energy effect | No energy effect. |
| 9. Reliability effect | All physical reliability-rate fields remain NOT_QUALIFIED. |
| 10. Carbon effect | No carbon effect. |
| 11. GREEN ranking effect | No ranking effect. |
| 12. ISCAS impact | Prevents topology-independent MBU claims and establishes the required coupling interface. |
| 13. Unsupported claims | Physical SBU/DBU/MBU rates; Altitude or Qcrit-scaled campaign conclusions |
| 14. Repository/integrity | PASS: baseline and final repository/external checkpoints, Attempts 1-9, protected DATE evidence, and frozen SRAM22 sources all verify. |
| 15. Recommended next action | Generate qualified bit maps, then drive physical upset geometries through the simulator. |

## Phase H: Carbon model

| Required item | Result |
|---|---|
| 1. Exact classification | NOT_QUALIFIED |
| 2. Proven | Embodied, operational, recovery, and total equations, units, gates, grid scenarios, and sensitivity axes are explicit.; Existing carbon calibration/default files are hashed and preserved read-only. |
| 3. Unproven | SKY130-specific manufacturing factor.; Qualified workload/lifetime energy.; Recovery carbon. |
| 4. Original vs corrected | Rows retain Liberty provenance, but neither model has qualified lifecycle inputs. |
| 5. U0/E0 matched results | U0/E0 carbon rows are generated only as blocked records. |
| 6. Five-seed robustness | All seeds remain blocked consistently. |
| 7. PPA effect | Physical area alone is insufficient for lifecycle carbon. |
| 8. Energy effect | Energy gating prevents operational carbon calculation. |
| 9. Reliability effect | No reliability result is converted into recovery carbon. |
| 10. Carbon effect | All lifecycle values are NOT_QUALIFIED. |
| 11. GREEN ranking effect | No ranking effect. |
| 12. ISCAS impact | Supplies an auditable model and sensitivity grid without fabricating carbon totals. |
| 13. Unsupported claims | Lifecycle carbon advantage; Grid-dependent winner; 28 nm proxy as SKY130 truth |
| 14. Repository/integrity | PASS: baseline and final repository/external checkpoints, Attempts 1-9, protected DATE evidence, and frozen SRAM22 sources all verify. |
| 15. Recommended next action | Qualify energy, lifetime/access counts, SKY130 manufacturing assumptions, and recovery policy. |

## Phase I: Integrated GREEN decision matrix

| Required item | Result |
|---|---|
| 1. Exact classification | BLOCKED_NO_FULLY_QUALIFIED_ROWS |
| 2. Proven | A 5,760-row Cartesian raw scenario matrix preserves source values, units, evidence labels, and missingness.; Normalization metadata records a bounded policy for future use. |
| 3. Unproven | Validated normalization bounds, EPC/ESII/NESII, or GREEN scores. |
| 4. Original vs corrected | Both original and corrected physical baselines remain distinguishable. |
| 5. U0/E0 matched results | Architecture rows are explicit; no forced comparison is made. |
| 6. Five-seed robustness | Seed is a matrix dimension. |
| 7. PPA effect | Available PPA remains raw. |
| 8. Energy effect | Energy is a blocking objective. |
| 9. Reliability effect | Physical reliability is a blocking objective. |
| 10. Carbon effect | Carbon is a blocking objective. |
| 11. GREEN ranking effect | Eligible rows: 0; normalized scores remain empty. |
| 12. ISCAS impact | Prevents a mathematically complete but scientifically unsupported ranking. |
| 13. Unsupported claims | GREEN winner; Normalized sustainability score |
| 14. Repository/integrity | PASS: baseline and final repository/external checkpoints, Attempts 1-9, protected DATE evidence, and frozen SRAM22 sources all verify. |
| 15. Recommended next action | Qualify each objective and freeze normalization bounds before scoring. |

## Phase J: Pareto and selector analysis

| Required item | Result |
|---|---|
| 1. Exact classification | BLOCKED_NO_FULLY_QUALIFIED_ROWS |
| 2. Proven | All 5,760 rows are deterministically screened and excluded with machine-readable reasons.; The existing deterministic selector is preserved as the baseline. |
| 3. Unproven | Pareto front, dominated solutions, hypervolume, knee points, and scenario winner. |
| 4. Original vs corrected | Liberty provenance is an explicit dimension. |
| 5. U0/E0 matched results | No U0/E0 Pareto claim. |
| 6. Five-seed robustness | Five seeds are retained but ineligible. |
| 7. PPA effect | PPA alone cannot determine the requested front. |
| 8. Energy effect | Energy objective unavailable. |
| 9. Reliability effect | Physical SDC/DUE objectives unavailable. |
| 10. Carbon effect | Carbon objective unavailable. |
| 11. GREEN ranking effect | No GREEN winner. |
| 12. ISCAS impact | Correctly stops analysis at the qualification gate and leaves a deterministic sorter for future complete rows. |
| 13. Unsupported claims | Sustainability-aware winner; Static-selector superiority/inferiority; NSGA-II result |
| 14. Repository/integrity | PASS: baseline and final repository/external checkpoints, Attempts 1-9, protected DATE evidence, and frozen SRAM22 sources all verify. |
| 15. Recommended next action | Re-run deterministic exact Pareto analysis after qualification; use NSGA-II only if the design space becomes non-enumerable. |
