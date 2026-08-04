# Thesis-ready Results, Discussion, Limitations, and Conclusion

## 1. Research question

This study asks which functionally verified ECC implementation is preferred under differing SRAM upset, workload, and reliability scenarios when exact software metrics are separated from analytical energy and carbon metrics. It further asks whether winner identity changes across scenarios and which reliability, redundancy, and decoder-complexity trade-offs explain the changes.

## 2. Experimental methodology

GREEN-ECC-PHY represents the mathematical code, encoder/codeword set, deployed decoder policy, verified capability, deployment architecture, scenario, and evidence backend as separate identities. The catalogue generator fixes all code manifests, field polynomials, matrices, decoder tables, scenario ranges, analytical coefficients, hard constraints, and selector ordering before the evaluation observes winners.

Functional behavior is evaluated exactly. For every selectable decoder, all masks in five error classes—single, adjacent double, non-adjacent double, adjacent triple, and non-adjacent triple—are executed on the canonical zero codeword. Because all selected encoders are linear and their deployed syndrome policies are translation invariant, the error-mask outcome does not depend on payload. The harness distinguishes correct recovery, detected/abstained outcomes, and silent miscorrection.

The analytical study spans 192 deterministic scenarios formed from two supply voltages, two temperatures, two scrub intervals, two carbon intensities, three error profiles, two workloads, and two reliability requirements. Statistical significance tests are neither needed nor used. Exact counts, deterministic sensitivity sweeps, Pareto membership, and regret are reported instead.

## 3. ECC portfolio

Fifteen distinct mathematical code specifications and 17 encoder/decoder implementations are registered. The portfolio contains Hsiao and conventional extended-Hamming SECDED; three decoder policies over the conventional codeword set; a preserved invalid cyclic candidate; a valid primitive BCH (63,51,t=2); shortened BCH (71,64,t=1), (78,64,t=2), and (85,64,t=3); and eight archived SafeForge/CodeForge matrix/table constructions. Fifteen implementations pass their guaranteed functional gate, while bounded SEC-DAEC and the historical cyclic candidate are rejected.

The repository also contains grouped generated-width SECDED, TAEC, SEC-DAEC, BCH-labelled, and Polar RTL, a Polar channel-bound model, TAEC coverage aliases, and C/C++ simulators. These artifacts are retained in the scope matrix with experimental, duplicate, rejected, or excluded status. No bit-exact (75,64)-I6/I7 TAEC definition was found, and no executable repository LDPC or Reed–Solomon code exists.

## 4. Functional verification results

Hsiao and conventional SECDED correct every single mask (72/72) and detect every double mask (2,556/2,556). The bounded TAEC policy passes that same SECDED universe but silently miscorrects all 62 adjacent triples over canonical data coordinates. It is therefore only partially verified and is never treated as a TAEC-capable construction.

The bounded SEC-DAEC policy fails: 302 of 2,556 double masks are silently miscorrected, and only 10 of 63 adjacent data pairs are corrected while 53 silently miscorrect. The historical cyclic/BCH-labelled code has exact minimum distance two and silently miscorrects 33 of 63 singles. Both remain visible but cannot enter selection.

The separate valid primitive BCH reference uses GF(2^6), primitive polynomial x^6+x+1, roots alpha^1 through alpha^4, and generator `1010100111001`. Its exact distance is five, and it corrects 2,016/2,016 masks through weight two. Valid parent-coordinate shortening yields (71,64,t=1), (78,64,t=2), and (85,64,t=3); their exhaustive totals are 71/71, 3,081/3,081, and 102,425/102,425 respectively. The t=3 code has a certified designed-distance lower bound of seven; an exact distance is not claimed because the exact dual-enumeration method is deliberately bounded to smaller redundancy.

## 5. Scenario and fairness methodology

Comparisons are normalized per information bit, 64-bit word, 512-bit cache line, workload, reliability requirement, and equal information capacity. Fragmentation and padding are charged explicitly. For example, a k=51 BCH requires two 63-bit codewords to protect one 64-bit word; the final 38 information coordinates are fixed padding.

The scenario model uses explicit sensitivity values rather than invented measurements. Expected corrected, DUE, and SDC probabilities are obtained by combining exact outcome fractions with each declared fault-class probability. Analytical dynamic, leakage, scrub energy, and operational carbon use the preregistered coefficient set. Each analytical field records units, model ID, provenance, evidence level, and sensitivity interval. All physical fields are null.

Candidates must pass verification and satisfy the scenario's SDC and DUE limits. Pareto filtering precedes a preregistered lexicographic selector over analytical total energy, decoder-complexity proxy, encoded payload bits, and stable identity.

## 6. Comparative results

All 192 scenarios have a feasible winner. Five implementations win:

- shortened BCH (71,64,t=1): 32 SBU-dominant/service scenarios;
- Hsiao SECDED: 64 SBU-stringent or adjacent-MBU/service scenarios;
- shortened BCH (78,64,t=2): 32 adjacent-MBU/stringent scenarios;
- SafeForge robust (72,64) abstaining decoder: 32 triple-stress/service scenarios; and
- shortened BCH (85,64,t=3): 32 triple-stress/stringent scenarios.

The winner transitions are explained by hard reliability constraints. A low-redundancy t=1 code is adequate under a permissive SBU profile. Hsiao's sparse SECDED structure is preferred when double errors primarily need safe detection. Under stringent adjacent-MBU reliability, exact double correction becomes necessary, selecting t=2 BCH. Under stringent triple stress, only the t=3 reference removes all modelled through-weight-three residuals. Under the service triple-stress budget, an abstaining SafeForge table is preferable in the analytical model because its higher DUE rate remains allowed while silent correction is avoided.

Primitive (63,51,t=2) and shortened (78,64,t=2) each appear on 160 of 192 Pareto fronts; t=3 appears on 128. The k=51 candidate's frequent Pareto membership does not imply frequent selection because its two-codeword payload framing substantially increases encoded bits.

## 7. Sensitivity and uncertainty

The base and storage-dominated energy models preserve every winner. A logic-dominated model preserves 190/192 winners (98.96%). The two changes are confined to SBU/service cases where two low-cost candidates are close. Thus, the scenario-region conclusion is stable under the tested coefficient ranges, but the precise low-severity winner is partly uncertainty-limited.

Fixed conventional SECDED is feasible in 96 scenarios and has 2.499% mean analytical energy regret over those cases. Hsiao is feasible in 96 and has 0.459% mean regret. Always using the strongest t=3 BCH is feasible in all 192 but incurs 21.937% mean analytical regret. These values are outputs of the sensitivity model, not energy measurements.

## 8. Negative results

The SEC-DAEC and historical cyclic implementations fail their guaranteed universes. The bounded TAEC label does not produce a TAEC capability. No complete (75,64)-I6/I7 construction exists in the repository. Polar artifacts lack a deployed deterministic decoder with an SRAM correction guarantee. Legacy family-level energy and transition reports cannot be mapped one-to-one to verified code/decoder identities and are excluded from selector-agreement claims.

The physical study remains negative. Structural Yosys output cannot establish cell area, routed area, critical path, dynamic or leakage energy, routing, MUX/controller overhead, transition/re-encoding cost, or physical uncertainty.

## 9. Threats to validity

The fault profiles and energy coefficients are uncalibrated sensitivity parameters. Error classes are uniform within each class and adjacency is linear within one canonical codeword; real SRAM physical placement, interleaving, banking, and cross-boundary bursts may differ. Workload activity is synthetic rather than traced. Reference BCH decoder tables are software structures and are not synthesized physical implementations. The archived SafeForge policies are exact for their tables, but their source distributions may not generalize. Only three coarse energy-parameter uncertainty models are swept.

The deterministic grid supports exact comparison only inside these assumptions. It does not establish statistical generalization, technology portability, or physical feasibility.

## 10. Supported conclusion

Different verified implementations win materially different preregistered scenario regions, and fixed baselines exhibit non-zero regret. Therefore, the strongest supported conclusion is:

> Scenario-aware ECC selection is supported within the declared software/analytical model. The useful selection boundary is driven primarily by required SDC/DUE limits and upset multiplicity, with redundancy and decoder-complexity proxies determining the lowest-modelled-cost feasible choice.

Sensitivity analysis preserves 190/192 or more winners, so the broad region structure is supported by the tested parameter ranges. The narrow low-severity boundary remains partially uncertainty-limited.

## 11. Unsupported claims

The evidence does not support a physical winner, measured energy or carbon saving, physical adaptive break-even, physical MUX/controller overhead, timing closure, routing feasibility, technology independence, radiation validation, temperature-chamber validation, or silicon validation. The parameterized adaptive condition is analytical only; its physical quantities remain null.

## 12. Reproduction commands

```text
python scripts/build_multi_ecc_catalogue.py
python scripts/run_multi_ecc_framework_evaluation.py
make
make test
python -m pytest -q
```

The machine record chain is `framework_summary.json` -> `software_study_summary.json` -> `scenario_selection_results.json`, with separate `exact_functional_profiles.json`, `normalized_exact_metrics.json`, `pareto_and_regret.json`, `uncertainty_and_sensitivity.json`, `architecture_compatibility_matrix.json`, and `plot_manifest.json` under `green_ecc_physical_simulation/multi_ecc_evaluation`.
