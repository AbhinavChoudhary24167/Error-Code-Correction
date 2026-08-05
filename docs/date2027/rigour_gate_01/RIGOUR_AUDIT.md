# GREEN-ECC DATE 2027 publication-rigour Gate 01

**Audit date:** 2026-08-04  
**Frozen target:** branch `main`, commit `f2908466bfa1a8eee8ad5c13b15e0d02a4730351`  
**Intended paper:** six-page DATE 2027 regular paper, T3 primary / D9 secondary  
**Gate-01 verdict:** **FAIL for publication readiness; CONDITIONAL PASS to proceed to Gate 02**

## Executive verdict

The repository cannot support the intended DATE 2027 regular-paper contribution today. It contains a substantial exact-functional and analytical-sensitivity framework, explicit rejected implementations, a finite analytical scenario study, and unusually candid existing limitations. It does not contain the decisive evidence for an implementation-aware cross-layer result: implementation-specific physical PPA/total-system energy, physical bit mapping and interleaving, calibrated fault inputs, or a complete runtime-transition implementation. Every physical objective in the current selection records is null.

The strongest existing evidence is exact and negative/functional: the historical cyclic candidate, SEC-DAEC policy, and TAEC adjacent-triple claim have explicit counterexamples, while the targeted existing BCH reference tests passed 10/10. Those results are bounded to their declared logical error universes and still require the dedicated Gate-02 revalidation before publication use.

The audit independently derived 15 code manifests, 17 implementation manifests, 17 architecture manifests, 15 selectable implementations under the existing status policy, and 192 scenario cells. All match the expected pre-audit counts. This agreement is not a reconciliation assumption and does not cure a reproducibility defect: in the disposable Git worktree, LF-to-CRLF conversion changes raw source SHA-256 values, so the registry loader, broad framework tests, and ECC verification fail before scientific execution.

The repository's current analytical study can support only a carefully qualified statement that scenario choices differ under its explicit assumed sensitivity model. It cannot support physical superiority, measured energy/carbon savings, absolute FIT, technology independence, runtime adaptation, or the intended H1–H4 paper conclusions.

## Audit boundary and method

Gate 01 inspected the entire frozen repository and existing correctness evidence. It did not generate a new minimum-distance proof, repair a decoder, redesign a code, extend a correctness universe, regenerate scientific results, or rewrite existing documentation. Potentially mutating builds/tests ran once in the detached disposable worktree `C:\Users\Abhinav\AppData\Local\Temp\green-ecc-rigour-gate-01-f2908466`. Only logs/manifests were copied here. No reset, checkout, clean, broad deletion, commit, push, or publication occurred.

Commands had explicit bounds: 30 seconds for inventory/tool/CLI inspection, 120 seconds for targeted tests/ECC verification, 300 seconds for `make`, 600 seconds for `make test` and RTL regression, and 900 seconds for full pytest/documentation checking. No executed command reached its timeout. The RTL regression was `NOT ASSESSABLE` because `bash` was unavailable; it was not retried indefinitely.

The original checkout was initially clean. At final inspection it may differ only by the new `docs/date2027/rigour_gate_01/` tree. Source and isolated state are recorded in `baseline/00_source_state_pre.log`, `baseline/01_isolated_state.log`, and `baseline/environment_manifest.json`.

## Independently derived inventory

| Item | Expected before audit | Independently derived | Method | Finding |
|---|---:|---:|---|---|
| Mathematical codes | 15 | 15 | Count and parse every `registry/codes/*.json` | Match |
| Implementations | 17 | 17 | Count and parse every `registry/implementations/*.json` | Match |
| Architectures | 17 | 17 | Count and parse every `registry/architectures/*.json` | Match |
| Selectable implementations | 15 | 15 | Existing verification records: 15 process passes, 2 failures; TAEC is capability-level partial | Match, with scope caveat |
| Scenario cells | 192 | 192 | `2 V x 2 T x 2 scrub x 2 CI x 3 fault x 2 workload x 2 requirements` | Match |
| Backend manifests | not supplied | 4 | Direct file enumeration | 1 structural-only, 3 unavailable/null |
| Existing verification reports | not supplied | 17 | Direct JSON enumeration | 15 process passes; 2 failures |
| Inventory/scope rows | not supplied | 30 | Existing `ecc_scope_matrix.json`/framework summary | Includes grouped unregistered/duplicate/excluded artifacts |

The expected and derived values agree exactly. The counts identify manifests and existing policy states; they do not prove mathematical equivalence, physical implementation distinctness, or publication validity. `baseline/19_registry_derivation.log` and `baseline/23_verification_and_scope.log` preserve the derivation.

### Repository structure and entry points

- Python framework/CLI: `eccsim.py`, `green_ecc_phy/`, `green_ecc_physical_simulation/`, `scripts/`, `analysis/`, `ml/`.
- C++ reference/demo programs: `src/`, root Makefile targets, unit tests.
- RTL/wrappers: `asic/`, `rtl/ecc_generated/`, generated Hsiao RTL.
- Tests: Python, unit, integration, golden CLI, Pareto, BCH, framework, and RTL scripts.
- Scientific configurations: registry code/implementation/architecture/backend/scenario/workload JSON; legacy `data/`, carbon defaults/calibration, experiment configs.
- Existing results: `green_ecc_physical_simulation/multi_ecc_evaluation/`, `reports/`, `docs/figure_data/`, figures and archived revision outputs.
- Manuscript-like sources: README, technical guide, framework report, documentation chapters, thesis/report material, archived drafts.
- Build systems: GNU Make, Python/pytest, Icarus/Yosys scripts, documentation generators, LaTeX.

The full static/file inventory is in `baseline/02_inventory.log`, `baseline/22_static_inventory.log`, and `baseline/23_verification_and_scope.log`. No Liberty, LEF, DEF, SDC, SPEF, VCD, SAIF, GDS/OASIS, identified PDK, or characterized SRAM macro was found. `scripts/run_safeforge_hardware_validation.py` and committed verification records contain host-specific absolute tool paths.

## Scientific gate table

| Gate | Outcome | Evidence | Reason |
|---|---|---|---|
| Frozen repository identity | `PASS` | source HEAD and branch logs | Source was `main@f2908466...`; only audit directory is authorized |
| Isolated execution | `PASS` | worktree state and command manifest | Mutating commands ran in detached disposable worktree |
| Cross-platform source identity | `FAIL` | `baseline/05_ecc_list.log`, `18_line_ending_diagnosis.log` | Raw hash changes under CRLF checkout; registry will not load |
| Tool/environment reproducibility | `FAIL` | doctor/tool logs | Python runtimes differ; wrong `libstdc++`; CMake/Bash unavailable; Verilator unreadable |
| Small C++ build | `PASS` | `baseline/12_make.log` | `make` completed, exit 0 |
| Golden CLI contracts | `PASS` | `baseline/07_targeted_golden.log` | 11 tests passed |
| Existing BCH reference tests | `PASS` | `baseline/08_targeted_bch.log` | 10 tests passed; not a new Gate-01 proof |
| Pareto unit/audit tests | `PASS` | `baseline/10_targeted_pareto.log` | 10 tests passed |
| Framework targeted tests | `FAIL` | `baseline/09_targeted_framework.log` | 12 failed/3 passed because registry hash rejected checkout bytes |
| `make test` | `FAIL` | `baseline/13_make_test.log` | 328 passed/12 failed; same registry/hash root cause |
| `python3 -m pytest -q` | `FAIL` | `baseline/14_python3_pytest.log` | 330 passed/12 failed; same root cause under second interpreter |
| Documentation reproducibility | `FAIL` | `baseline/15_documentation_check.log` | Seven generated CSVs reported stale |
| Existing RTL regression | `NOT ASSESSABLE` | `baseline/16_rtl_regression.log` | `bash` not available; one attempt only |
| Registry catalogue completeness | `CONDITIONAL PASS` | direct manifest and source inventory | Registered counts reconcile; unregistered/generated/wrapper/duplicate artifacts are now mapped; loader remains nonportable |
| Mathematical identities/correctness | `NOT ASSESSABLE` | existing records and targeted BCH tests | Gate 01 may inspect but not perform Gate-02 validation; positive statuses remain provisional |
| Rejected/partial decoder visibility | `PASS` | per-implementation verification JSON | Cyclic and SEC-DAEC rejected; TAEC triple capability not promoted |
| Physical mapping/interleaving | `NOT IMPLEMENTED` | scenario and architecture manifests | Current adjacency is logical consecutive codeword coordinates, not physical cells |
| Raw fault calibration/absolute FIT | `FAIL` | scenario PMFs, Qcrit example, reliability docs | Fault probabilities are assumed; Qcrit provenance is example/unverified; no target physical map |
| Scrub/accumulation traceability | `CONDITIONAL PASS` | analytical model/source | Equations/parameters exist, but inputs and system validation are uncalibrated |
| Implementation physical PPA | `NOT IMPLEMENTED` | characterization/backend records | All physical area/timing/power/energy/routing fields are null |
| Total-system energy | `FAIL` for physical claim | analytical model/config | Current values are derived from assumed per-bit/XOR/leakage constants and structural proxies |
| Operational carbon | `CONDITIONAL PASS` as equation; `FAIL` as independent objective | energy/carbon docs and scenario config | Within each scenario it is a positive scalar multiple of energy |
| Embodied carbon | `NOT IMPLEMENTED` | framework summary/model audit | No implementation physical area or sourced allocation/yield/lifetime chain |
| Fair useful-capacity normalization | `CONDITIONAL PASS` | comparison/study code and docs | Integer codeword/padding logic exists; physical memory/codec/controller boundary is absent |
| Exhaustive enumeration feasibility | `PASS` for current space | 15 candidates x 192 scenario records; source inspection | Exact enumeration is trivially feasible; full cross-layer factors are not yet implemented |
| Pareto implementation | `CONDITIONAL PASS` | targeted tests and committed audits | Mathematical tests pass, but current frontiers use analytical/proxy records and docs outputs are stale |
| NSGA-II methodology | `FAIL` as claimed method/need | source inspection | `_nsga2_sort` is deterministic nondominated sorting, not population-based NSGA-II; exact enumeration is feasible |
| Runtime adaptation | `NOT IMPLEMENTED` | architecture manifests/reference controllers/framework summary | No complete migration/re-encoding, codeword compatibility, metadata, or measured overhead |
| Claims/provenance | `FAIL` | claims ledger and search logs | 27% energy, 19% carbon, 189 scenarios, 14 nm/measured/physical claims lack complete chains |
| Current DATE regular-paper readiness | `FAIL` | all gates | Central intended H1–H4 evidence is incomplete |
| Progression to Gate 02 | `CONDITIONAL PASS` | contract/catalogue/traceability | Evidence map exists; hash portability must be the Gate-02 entry fix |

## ECC correctness evidence boundary

The detailed identities, registered implementations, generated widths, wrappers, C++/Python duplicates, Polar artifacts, legacy aliases, and literature-only mentions are in `ECC_CATALOGUE.md`.

Existing records state:

- conventional and Hsiao SECDED pass 72/72 singles and 2556/2556 doubles in their declared logical SECDED universe;
- the repository cyclic `(63,51)` candidate has recorded exact `d=2`, corrects 30/63 singles, and silently miscorrects 33/63;
- the valid primitive `(63,51,t=2)` BCH reference is a distinct construction with existing exact `d=5` and 2016/2016 mask record;
- shortened BCH references have existing 71/71 (t1), 3081/3081 (t2), and 102425/102425 (t3) records; t3 has only designed `d>=7` in its manifest;
- bounded SEC-DAEC silently miscorrects 302/2556 doubles and 53/63 adjacent pairs;
- bounded TAEC passes only the shared SECDED scope and silently miscorrects 62/62 existing adjacent triples;
- no distinct `(75,64)` I6/I7 TAEC matrix/encoder/decoder was found.

These are reports of existing evidence, not new Gate-01 exhaustive results. Physical adjacency is not established, and no guarantee extends beyond the declared mask universe. Gate 02 must revalidate every intended identity and miscorrection domain.

## Fault-to-reliability trace

| Stage | Current source | Evidence class | Audit result |
|---|---|---|---|
| Raw fault arrival | scenario class probabilities; legacy Hazucha-style functions and Qcrit file | `ASSUMED` / `DERIVED` | No target silicon/radiation calibration; absolute FIT unsupported |
| Spatial/temporal distribution | SBU/adjacent/non-adjacent double/triple PMFs; independent/Poisson-like accumulation | `ASSUMED` | Explicit sensitivity presets, not measured spectra; independence not validated |
| Physical-to-logical mapping | consecutive encoded coordinates | `ASSUMED` | Not a physical cell map; no interleaving/layout/bitline geometry |
| Conditional decoder outcome | exact existing per-mask records for registered policies | `SIMULATED` | Strong within declared logical universes; positive status provisional for Gate 02 |
| Accumulation/scrubbing | scrub intervals 1/3600 s and analytical formulas | `DERIVED` from `ASSUMED` | Trace exists mathematically but lacks calibrated inputs/system validation |
| Residual SDC/DUE | exact fractions combined with assumed PMFs | `DERIVED` | SDC/DUE are distinguished; absolute probability remains conditional |
| System/FIT conversion | legacy fitted model/exposure scaling | `DERIVED` from `ASSUMED` | Qcrit/source/area/flux/environment and system exposure unresolved |

Safe reporting is limited to conditional decoder coverage, explicit existing counterexamples, and sensitivity analysis. No absolute FIT, annual-error, silicon-reliability, radiation-qualification, or realistic physical-adjacency claim passes.

## Hardware, energy, and carbon evidence classification

| Quantity | Actual source | Class | Publication disposition |
|---|---|---|---|
| Matrix/XOR/table counts | code/decoder structure | `PROXY` | May be called structural complexity only |
| Generic Yosys cells/depth | structural synthesis without Liberty/PDK | `SYNTHESIZED` only as generic structure; `PROXY` for physical PPA | Not physical area/delay |
| Cell area / routed area | null | `UNRESOLVED` | Not computable |
| Critical path / physical latency | null; cycle/combinational protocol separately represented | `UNRESOLVED`; structural depth is `PROXY` | No timing/PPA claim |
| Dynamic codec/memory energy | per-bit and per-XOR constants in scenario config | `DERIVED` from `ASSUMED`/`PROXY` | Analytical sensitivity only |
| Leakage energy | assumed stored-bit coefficient and temperature multiplier | `DERIVED` from `ASSUMED` | Analytical sensitivity only |
| Scrub energy | assumed read/write multiplier and traffic | `DERIVED` from `ASSUMED` | Analytical sensitivity only |
| Total-system energy | analytical sum without characterized macro/controller/transition/routing | `DERIVED` from `ASSUMED`/`PROXY` | Must not be called measured or physical total energy |
| Physical power / activity-based power | no VCD/SAIF, library, macro, raw report | `UNRESOLVED` | Not computable |
| Operational carbon | analytical energy / 3.6e6 x scenario CI | `DERIVED` from `ASSUMED` | Rank-identical to energy within every current scenario |
| Embodied carbon | placeholder/default factors; no physical areas/allocation/yield/lifetime | `UNRESOLVED` | Not implemented |
| 27% energy / 19% carbon | no complete chain | `UNRESOLVED` | Remove |

No repository result qualifies as `MEASURED`. Physical PPA values are not merely uncertain; they are absent.

## Selector and design-space audit

The current selectable set is 15 implementation records evaluated across 192 analytical scenarios. Rejected records remain visible. Architecture manifests exist, but architecture, mapping, interleaving, and concrete transition costs are not fully materialized as exhaustive candidate axes. The present study applies verification/fairness/reliability filters, builds an exact zero-epsilon five-objective analytical frontier, and chooses the lexicographic minimum `(analytical total energy, structural complexity, encoded bits, implementation_id)`.

Exact enumeration is feasible: the recorded scale is only 2880 candidate-scenario evaluations before filtering. The code name `_nsga2_sort` does not implement an evolutionary NSGA-II loop: no population evolution, crossover, mutation, termination, or optimization seeds exist. NSGA-II is therefore neither used nor justified at this scale.

ESII/GS/NESII are legacy diagnostic composite scores, not the current winner rule. NESII is a monotone cohort normalization of ESII and cannot create independent information; composite rankings remain sensitive to weights/anchors. The current operational-carbon objective is mathematically redundant within each scenario because `carbon = positive_constant_scenario x energy`. Hypervolume is a documentation audit using a data-derived reference point and does not select winners. Targeted Pareto tests pass, but documentation check mode reports stale generated files.

The existing fixed-baseline regret is not H1: it does not apply the frozen mathematical-code-to-canonical-implementation restricted procedure and uses a legacy analytical comparison. The experiment contract now fixes the non-tautological endpoint, equation, mapping rule, statistics, seeds, exclusions, interaction metric, practical threshold, and carbon null rule.

Selection is presently design-time analytical software. Reference mode/transition controllers and architecture manifests do not implement deployed runtime adaptation. Complete codeword compatibility, metadata, migration/re-encoding, failure semantics, and characterized transition overhead are absent.

## Claims and provenance reconciliation

The broad raw repository search was deliberately over-inclusive (199225 matches and an exit status 2 due Windows path/glob handling) and is retained as `baseline/20_claim_search.log`; it is not used as a denominator. A successful scoped search of publication-facing Markdown/LaTeX sources produced 938 pattern hits in `baseline/21_manuscript_claim_inventory.log`. Most hits are section titles, formulas, commands, source paths, limitations, or repeated methodological terms rather than assertive paper claims. Manual adjudication produced 35 location-specific publication-relevant occurrences in `CLAIMS_LEDGER.csv`.

The reconciliation rule was conservative: all numerical outcomes, capability/validation wording, physical/measurement wording, scenario/count claims, carbon/energy/FIT claims, selector/Pareto/hypervolume/robustness claims, and runtime/adaptive claims in the main README/guide/report and authoritative limitation/model chapters received ledger rows. Historical/archive mentions of 27%, 19%, 189, 14 nm, and measured results are represented by unresolved headline rows even when the current text disavows them. Non-assertive navigation, definitions, commands, code excerpts, and explicit repeats of the same limitation without a new result were excluded from row multiplication. No excluded hit is treated as evidence for a paper claim.

Every ledger row records a `path:line`. Broken table/figure-to-raw-to-script-to-configuration/model chains are `UNRESOLVED`. `TRACEABILITY_MATRIX.csv` maps each intended DATE claim/figure to the evidence that would be required; no intended primary claim currently passes.

## Findings by severity

### Fatal

1. **The central evidence category is absent.** No implementation-specific, common-flow physical area/timing/power/energy or SRAM macro evidence exists. H1/H2 cannot establish implementation-aware physical loss or dependence.
2. **Clean-checkout scientific identity is nonportable.** Registry raw-byte hashes reject CRLF-converted files. The main test/evaluation path fails in the isolated frozen worktree.
3. **Gate 02 is unfinished.** Positive mathematical/decoder guarantees have not passed the dedicated independent identity/miscorrection gate; two registered implementations already fail and TAEC is partial.
4. **Physical fault context is missing.** PMFs and Qcrit are assumed/example inputs; logical adjacency is not physical mapping/interleaving. Absolute reliability/FIT is unsupported.
5. **The contracted hypotheses have no production data.** Current legacy regret does not implement H1; same-code PPA (H2), executable interactions (H3), and nonredundant carbon (H4) are absent.

### Major

- Environment/toolchain identity is split and host-specific; RTL regression is not assessable.
- Documentation check mode fails on seven stale CSV outputs.
- Current analytical total energy omits physical macro, routing, activity, controller, transition, and re-encoding evidence.
- Runtime adaptation is described but not end-to-end implemented.
- Comparisons across different `(n,k)` depend on analytical capacity normalization and lack physical memory-boundary evidence.
- Only three deterministic energy scaling cases support current “stability”; this is not statistical confidence or general robustness.
- Architecture manifests and wrappers can be mistaken for independent implemented design points.

### Minor/methodological

- Data-derived hypervolume reference prevents strong cross-study interpretation.
- `measured correction fraction` wording in a reliability equation can be confused with hardware measurement; it is functional simulation/enumeration.
- Committed records contain host-specific absolute tool paths.
- Submodule status was not assessable because Git helper dependencies were missing, although no submodule content was otherwise indicated by the inventory.

## Five most serious blockers

1. Missing common-flow implementation-specific physical PPA and total-system energy evidence.
2. Checkout/line-ending-sensitive registry hashes that break clean isolated reproduction.
3. Incomplete Gate-02 mathematical identity, decoder correctness, and exhaustive miscorrection validation.
4. Uncalibrated fault/Qcrit inputs and absent physical mapping/interleaving, preventing absolute reliability claims.
5. No data implementing the frozen H1 restricted baseline, H2 paired PPA, H3 cross-layer interactions, or H4 carbon non-redundancy.

## Commands and outcomes

The machine-readable record is `baseline/command_manifest.json`; raw logs are in `baseline/`.

| Command | Timeout | Outcome |
|---|---:|---|
| repository/worktree state, inventory, versions, dependency capture | 30 s each | partial/pass; submodule helper and some version probes failed |
| `python eccsim.py doctor --json` | 30 s | process 0, application `error` |
| `python eccsim.py ecc list` | 30 s | exit 2, broken source hash after CRLF checkout |
| golden CLI tests | 120 s | 11 passed |
| existing BCH reference tests | 120 s | 10 passed |
| targeted framework/study tests | 120 s | 12 failed, 3 passed |
| targeted Pareto tests | 120 s | 10 passed |
| bounded Hsiao verification command | 120 s | exit 2 at registry hash gate |
| `make` | 300 s | pass |
| `make test` | 600 s | exit 2; 328 passed, 12 failed |
| `python3 -m pytest -q` | 900 s | exit 1; 330 passed, 12 failed |
| `python scripts/build_documentation.py --check` | 900 s | exit 1; seven CSVs stale |
| `bash asic/scripts/regress.sh` | 600 s | `NOT ASSESSABLE`; Bash unavailable |

No command timed out. No failed command was silently repaired or rerun as though successful.

## Limitations of this audit

- Gate 01 deliberately did not perform the new proofs/exhaustive validation reserved for Gate 02; it reports existing evidence only.
- Proprietary/external PDK, SRAM, measurement, radiation, workload, and carbon datasets not present in the repository were not assessed.
- The disposable worktree's CRLF behavior prevents an end-to-end clean pipeline result; committed outputs were inspected but not accepted as freshly regenerated.
- RTL regression was not assessable because the declared shell was unavailable. Generic `make` and Python tests do not substitute for it.
- Claim-search adjudication is semantic: raw lexical hits include many non-claims. The ledger covers publication-relevant assertions in main sources and all named historical headline risks, not every occurrence of words such as “energy” in source code or JSON.
- Gate 01 judges evidence at the frozen commit; later changes/results require a new gate and cannot inherit this verdict.

## Mandatory verdict answers

1. **Would the current repository support a DATE 2027 regular-paper submission today?** No. It does not support the intended implementation-aware cross-layer contribution or publication-grade physical/reliability claims.
2. **Which single missing evidence category is most fatal?** Common-flow, implementation-specific physical characterization and total-system energy evidence, including the SRAM macro and all codec/architecture overhead.
3. **Which current headline claim is least defensible?** A 19% carbon reduction. No provenance chain exists, current operational carbon is rank-identical to energy within a scenario, and embodied carbon is absent.
4. **Which existing result is strongest?** The bounded exact-functional counterexample evidence: cyclic, SEC-DAEC, and TAEC failures are explicit and falsifiable; the valid BCH reference also has passing targeted existing tests. Publication use still requires Gate 02.
5. **Is the current ECC catalogue scientifically comparable?** Only conditionally for exact functional/analytical comparisons after equal-useful-capacity normalization. It is not a fair physical PPA catalogue, and unregistered/wrapper/duplicate identities must stay excluded or explicit.
6. **Is NSGA-II justified by the current design-space size?** No. Exact enumeration of the present 15-by-192 records is feasible, and the current code does not implement an evolutionary NSGA-II loop.
7. **Is carbon currently an independent objective?** No. Operational carbon is a positive within-scenario scaling of energy; candidate-dependent embodied carbon is unavailable.
8. **Is runtime adaptation actually implemented?** No. Manifests and reference controllers exist, but complete migration/re-encoding, compatibility, metadata, failure behavior, and characterized overhead do not.
9. **Which claims must be removed immediately?** 27% energy reduction; 19% carbon reduction; 189-scenario result; universal selector agreement; 14 nm/measured/synthesized physical result; physical PPA winner; absolute FIT/silicon/radiation validation; technology independence; measured adaptive break-even; implemented runtime adaptation; and general SEC-DAEC/TAEC/BCH-family guarantees that exceed the specific passing implementation universe.
10. **Is the repository ready to proceed to the mathematical-correctness implementation gate?** Conditionally yes. The catalogue, claim ledger, risks, and experiment contract now define the work, but Gate 02 must begin by making scientific content identity checkout-stable and then validate every matrix/polynomial, encoder/decoder pair, declared universe, and miscorrection domain.

**Exact next gate:** **Gate 02 — mathematical correctness and exhaustive miscorrection validation.**
