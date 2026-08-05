# Execution plan to DATE 2027

**Start state:** Gate 01 completed against `main@f2908466bfa1a8eee8ad5c13b15e0d02a4730351` on 2026-08-04.  
**Official deadlines:** abstract registration **2026-09-13 AoE**; final paper submission **2026-09-20 AoE**. Verify the dates again on the [DATE call for papers](https://www.date-conference.com/authors/call-for-papers) before submission.  
**Scheduling rule:** evidence generation precedes figures and prose. A missed fatal-gate deadline triggers an explicit scope/no-submission decision; it does not authorize proxy substitution.

## Dependency chain

`Gate 01 contract -> Gate 02 correctness -> fair tuple registry -> reproducible physical/fault flows -> preregistered runs -> independent analysis -> claim gate -> paper`

Only work that depends on completed evidence may proceed in parallel. The audit directory remains immutable evidence; Gate 02 and later work use new, separately reviewed locations.

## 0. Freeze and triage — 2026-08-05 to 2026-08-07

**Inputs:** this audit, frozen commit, existing rejected/partial records.  
**Outputs:** reviewed Gate-01 sign-off; machine-readable deviation log; checkout-stable environment/identity decision.

1. Review the five fatal blockers and accept `EXPERIMENT_CONTRACT.md` without observing new outcomes.
2. Define a portable interpreter/tool environment and required/optional tools. Resolve the Python/Python3 split, runtime-library resolution, Bash/RTL runner, and Verilator status.
3. Fix the scientific artifact identity mechanism so LF/CRLF checkout cannot alter a declared source identity, or enforce canonical LF at checkout and verify it on every supported host. Add fresh-checkout tests; do not rewrite scientific results during diagnosis.
4. Freeze the Gate-02 implementation list and exact existing claimed universes. Rejected implementations remain visible; no favourable relabelling or silent replacement.

**Exit:** registry loads and its expected-failure fixtures behave identically in fresh isolated checkouts; environment manifest is reproducible; no implementation status has been changed without Gate-02 evidence.  
**No-go:** unresolved source identity by 2026-08-07.

## 1. Gate 02 — mathematical correctness and exhaustive miscorrection validation — 2026-08-06 to 2026-08-11

This is the exact next gate. It—not documentation, plotting, physical optimization, or new code design—must happen first.

1. Reconstruct each registered mathematical identity from matrix/polynomial sources and cross-check dimensions, rank, systematic layout, parity treatment, shortening/extension, and source hashes.
2. Independently validate valid primitive/shortened BCH construction; keep the degree-12 cyclic candidate separate. Never infer BCH capability from a label.
3. Establish encoder/decoder/RTL-reference equivalence for every selectable implementation and identify wrappers/duplicates.
4. Execute every predeclared correction/detection universe; enumerate miscorrection outcomes within the frozen scope; state any data-independence argument. New universes or proofs must be separately preregistered within Gate 02.
5. Reproduce the existing cyclic, SEC-DAEC, and TAEC counterexamples. A disagreement is a blocking investigation, not a reason to discard the negative result.
6. Emit immutable per-mask/per-universe records, hashes, counterexamples, tool/seed manifests, and code/implementation gate statuses.

**Exit:** every candidate is `PASS`, `CONDITIONAL PASS` with an exact surviving scope, or `FAIL`; an independent verifier reconciles all counts and universe hashes.  
**No-go:** any intended candidate has unresolved encoder/decoder identity or unexplained miscorrection by 2026-08-11.

## 2. Candidate and fairness freeze — 2026-08-10 to 2026-08-19

Depends on candidate-level Gate-02 results; schema work may start earlier, but no winner result may be generated.

1. Materialize the full finite tuple `(code, implementation, architecture, mapping, interleaving, scrub, PVT, workload, fault environment)`.
2. Freeze the mathematical-only canonical mapping. Conventional extended Hamming maps to `secded-rtl-combinational-72-64-v1`; sole registered implementations map to themselves; unsupported/rejected canonical choices remain infeasible.
3. Make mapping and interleaving executable, with a physical-cell-to-logical-coordinate record. Freeze scrub state/accumulation semantics and SDC/DUE definitions.
4. Add equality checks for useful information capacity, integer codewords/padding, macro/storage expansion, codec and controller boundaries, target timing, activity/workload, PVT, fault inputs, and seeds.
5. Count every full and restricted tuple before outcomes. Estimate exact enumeration runtime and storage. Retain exact enumeration unless the recorded bound makes it infeasible.
6. Freeze scenario inclusion/exclusion codes and a holdout-free rule: no cell may be removed after outcome inspection.

**Exit:** schema-valid machine-readable tuple and canonical-mapping manifests with hashes; independent counts agree; every tuple resolves to a Gate-02 status and fair context.  
**No-go:** incomplete executable mapping/interleaving or unfair capacity/physical boundary by 2026-08-19.

## 3. Physical and reliability flow qualification — 2026-08-08 to 2026-08-28

This is the schedule-critical parallel stream. It may qualify infrastructure before Gate 02 completes, but production candidate runs must wait.

### Physical flow

1. Select and document the target technology/library, SRAM macro/data, PVT corners, timing constraints, tool versions/licenses, routing extraction, and activity source.
2. Define total-system boundaries including encoder, decoder, parity storage/macro widening, MUX/controller, metadata, scrub traffic, transition, and re-encoding.
3. Dry-run one non-scientific fixture through the complete flow by **2026-08-18**. Validate units and raw-report parsing; never impute a failed metric.
4. Qualify deterministic handling of the five common paired seeds and archive raw logs/netlists/reports with hashes.

### Reliability flow

1. Decide by **2026-08-12** whether absolute FIT can be supported. If Qcrit/flux/geometry/MBU inputs cannot be calibrated, freeze the paper to conditional coverage/sensitivity and prohibit absolute/reality wording.
2. Trace raw arrivals -> spatial/temporal distribution -> physical mapping -> decoder outcome -> accumulation/scrub -> residual word/system SDC/DUE -> any time/FIT conversion.
3. Validate units, probability conservation, SDC/DUE separation, confidence intervals, Monte Carlo stopping/convergence, and exact-versus-sampled labels.
4. Source system tolerances for the practical-effect criterion or commit to descriptive effect reporting only.

**Exit:** raw-to-metric dry run with no unresolved primary field; independent unit/provenance audit passes.  
**No-go:** no physical dry run by 2026-08-18; no defensible reliability scope by 2026-08-12.

## 4. Pilot and analysis lock — 2026-08-20 to 2026-08-25

1. Run a bounded pilot solely to validate plumbing, runtime, missingness, and units. Do not use pilot outcomes to choose hypotheses, mappings, effect thresholds, axes, or exclusions.
2. Freeze primary/secondary endpoint code, regret equation, BCa bootstrap (10,000; seed 1723), Clopper-Pearson/Bonferroni method, difference-in-differences, factorial terms, BH 5%, five physical seeds, and tie-breaking.
3. Freeze raw schemas and provenance DAG. Each planned table/figure must resolve through `TRACEABILITY_MATRIX.csv`.
4. Decide H4 by 2026-08-25: if no candidate/time/location-dependent carbon can change a decision, declare carbon redundant and remove it from the objective vector.
5. Decide runtime-adaptation scope: if complete migration/re-encoding/metadata/transition functionality and characterizable overhead cannot finish by 2026-08-26, remove runtime implementation claims.

**Exit:** signed/hash-frozen analysis package and successful synthetic/fixture validation; no production outcomes inspected.  
**No-go:** any primary endpoint input, exclusion, or practical-effect rule remains mutable.

## 5. Production experiments — 2026-08-26 to 2026-09-02

1. Run Gate-02-passing candidates only, with one recorded attempt per run unless the preregistered failure policy authorizes a new run. Never choose a favourable seed/run.
2. Execute all five common physical-design seeds for every comparable implementation and every required scenario/factor cell.
3. Run the full exhaustive selector and restricted canonical selector on identical records. Record infeasibility and exclusions explicitly.
4. Execute the frozen cross-layer factorial/fault study. Preserve raw outcomes; do not aggregate away SDC versus DUE or failed cells.
5. Hash all raw outputs, commands, tools, configurations, and model inputs. Use immutable run IDs and a manifest that rejects unlisted files.
6. Capture resource/time bounds showing whether exact enumeration remains feasible. Do not introduce NSGA-II during production.

**Exit:** complete raw manifest; zero unexplained missing eligible cells; run-status audit passes.  
**No-go:** incomplete same-code physical data for H2 or missing primary H1 cells by 2026-09-02.

## 6. Independent analysis and falsification — 2026-09-01 to 2026-09-06

1. Independently recompute feasibility, objective units, Pareto sets, lexicographic decisions, restricted/full disagreement, regret, effect distributions, CIs, and interaction statistics from raw records.
2. Run negative/mutation controls for selector feasibility, dominance, mapping, unit conversion, and evidence-null handling.
3. Reconcile physical report totals and useful-capacity boundaries. Inspect seed variance and report failed timing/runs per the frozen policy.
4. Test energy versus carbon rank equality exactly. A null H4 removes carbon as an optimization objective.
5. Report every hypothesis null. Do not search for a new endpoint after results.
6. Update the claims ledger with a complete `claim -> table/figure -> processed -> raw -> script -> configuration -> model input` chain.

**Exit:** independent analysis matches producer output; every intended claim has an allowed evidence class and acceptance result.  
**Submission go/no-go:** **2026-09-06**. If H1/H2 lack the contracted evidence, the intended regular-paper claim set is no-go.

## 7. Paper construction and artifact rehearsal — 2026-09-06 to 2026-09-12

1. Write methods/results from accepted ledger rows only. State null and negative results, exclusions, uncertainty, and evidence boundaries.
2. Use no more figures/tables than the six-page format can support; each is generated from an accepted traceability row. No decorative plot substitutes for missing evidence.
3. Perform an adversarial internal review: correctness, fairness, statistical methods, physical boundary, carbon redundancy, terminology, and claim-chain spot checks.
4. Reproduce the artifact from a fresh frozen environment with explicit timeouts. Required commands include `make`, `make test`, `python3 -m pytest -q`, documentation check, Gate-02 verification, physical/report validation, and analysis replay.
5. Scan the entire submission for prohibited `27%`, `19%`, `189`, unsupported `14 nm`, measured/silicon/radiation, NSGA-II, runtime/adaptive, best/optimal/robust, and physical-PPA wording.

**Exit:** six-page draft, supplement/artifact manifest, zero unresolved cited claims, fresh-environment reproduction pass.  
**No-go:** any primary result lacks raw-to-claim traceability by 2026-09-12.

## 8. Abstract registration — 2026-09-13 AoE

Register only a title, abstract, authors, topics, and claim scope already supported by the 2026-09-06 go decision. Do not register a stronger physical/carbon/runtime claim in anticipation of unfinished work. Archive the submitted metadata and timestamp.

## 9. Final verification and submission — 2026-09-14 to 2026-09-20 AoE

1. Freeze data/analysis by 2026-09-14; after that, changes are corrections with an impact log, not result shopping.
2. Run independent numbers/units/table/figure checks and confirm anonymization, format, page limit, citations, and topic selection.
3. Re-run the claims-ledger/traceability validator and fresh artifact smoke by 2026-09-17.
4. Freeze PDF and artifact hashes by 2026-09-19; compare the final abstract/conclusion to accepted ledger claims.
5. Submit before **2026-09-20 AoE**, retain receipts and immutable submitted files, and avoid deadline-hour generation.

## Command policy for all later gates

Use an isolated worktree or immutable copy for potentially mutating commands. Give every command one attempt and an explicit timeout appropriate to its class; record `TIMEOUT` and do not loop indefinitely. Copy only logs/manifests/results explicitly belonging to that gate. Never use reset, checkout, clean, or broad deletion to repair the source tree. A failed command remains a finding until its root cause and scientific impact are documented.
