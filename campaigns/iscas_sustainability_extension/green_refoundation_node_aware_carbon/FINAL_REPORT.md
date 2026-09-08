# GREEN refoundation and node-aware carbon: final report

## Executive outcome

The campaign classification is
`GREEN_METRIC_REFOUNDED_PARTIAL_QUALIFICATION`. GSE/GCI survive the formal
audit, the carbon and lifecycle equations are auditable, deterministic
uncertainty is propagated, and exact logical reliability controls are joined
into GREEN matrix v2. The current evidence does **not** qualify absolute SKY130
manufacturing carbon, operational energy, physical reliability rates,
lifecycle carbon, any GSE/GCI matrix value, or an ECC winner. Historical Gate-3
remains independently `FAIL`.

## Required answers

### 1. What dead/redundant code was removed?

Phase 0 removed 146 proven disposable targets: Python/pytest caches, untracked
UUID test workspaces, and ordinary rebuildable compiler/executable
intermediates. No code was labelled `DEAD_CODE`; the evidence did not justify
that stronger claim. An initially misclassified set of 120 tracked ML fixtures
was restored before the cleanup commit, and the audit now enforces
`TRACKED_IMPLIES_KEEP_SOURCE_OF_RECORD`.

### 2. What was preserved and why?

Attempt09 (2,098 files, 5.13 GB) and Attempt10 (302 files, 51.4 MB), protected
DATE material, all 565 tracked source inputs, seven calibration inputs, SRAM22
assets, Liberty/LEF/GDS sources, historical failures, manifests, and seven
ambiguous root outputs were retained. They are source-of-record, protected
history, provenance evidence, or insufficiently understood to delete safely.

### 3. Did cleanup change any historical result?

No. Attempt09 and Attempt10 tree fingerprints match before and after cleanup;
tracked source and calibration hashes match; protected DATE diffs are empty;
and the simulator executable is restored byte-for-byte after builds.

### 4. What mathematical defects exist in the legacy metrics?

The claimed harmonic bound is reversed: for positive normalized weights,
`H_w >= min(S_i)`, not `H_w <= min(S_i)`. Epsilon floors leak nonzero score at
zero utility. NESII and deployed selector preprocessing depend on the candidate
cohort. Fixed anchors are unit-sensitive, arbitrary weights allow rank reversal,
missing carbon can be rewarded by weight renormalization, and energy can be
double-counted through both energy utility and operational carbon. ESII-v1 also
has perverse behavior at its near-zero-carbon threshold.

### 5. Which legacy metrics remain useful?

ESII, NESII, and both GREEN Score generations remain
`LEGACY_COMPATIBILITY_METRICS` for reproducibility, sensitivity, and rank-
reversal diagnostics. EPC remains a conditional energy-per-correction
diagnostic when its event count and energy boundary are explicit. None is an
admissible primary selection metric here.

### 6. What is the new functional unit?

One correct payload-bit memory service delivered under the declared workload
and service policy. For fixed payload `B`, transaction count `N`, and exhaustive
mutually exclusive outcome probability `Q`, useful service is `S = B N Q`.
Requested access, detected failure, SDC, or SLA-violating output receives no
useful-service credit.

### 7. What is the new primary GREEN metric?

`GSE = S/C_LC` in correct useful payload bits per kgCO2e; its reciprocal is
`GCI = C_LC/S`. The matched-baseline form is
`GSE_R = (Q_c/Q_U0)(C_LC,U0/C_LC,c)`.

### 8. What mathematical properties are proven?

On `S >= 0, C_LC > 0`, GSE is dimensionally consistent, well-defined, strictly
increasing in service, non-increasing in carbon, dominance-consistent,
candidate-set independent, unit-scaling consistent, baseline-relative
interpretable, weight- and cohort-independent, asymptotically sensible,
samplewise compatible with uncertainty, and compatible with exact Pareto
dominance. Deterministic randomized/exhaustive tests cover all 13 required
properties.

### 9. What properties failed?

None of the required GSE properties failed on its declared domain. GCI is
undefined at zero useful service by design. The metric does not supply missing
evidence, invent an acceptable SDC threshold, or select a risk preference;
those are boundary conditions, not hidden score behavior.

### 10. Is GSE retained or replaced?

Retained, with GCI and exact Pareto analysis. Retention of the formula does not
qualify any current numerical architecture result.

### 11. What is the wafer-carbon equation?

`C_wafer(n,r,g,a,t) = C_scope1 + C_scope2 + C_upstream`, with
`C_scope2 = E_fab × CI_fab` and
`C_scope1 = sum_j(M_j EF_j release_j (1-eta_j))`. Upstream contributions remain
separate and incomplete Scope 3 is never called full lifecycle carbon.

### 12. What is the good-die carbon equation?

`C_good_die = C_wafer/N_good + C_maskset/N_production_good_dies + C_package + C_other`,
where `N_good = N_gross × Y_die × Y_line`. Missing mask, package, or other
burdens remain explicit rather than silently zeroed in qualified claims.

### 13. How is yield modeled?

Gross dies use a circular-wafer edge-loss approximation. Die yield supports
Poisson, negative-binomial, and Murphy equations; line yield is separate.
Defect density, clustering, die area, and line yield are explicit inputs with
evidence labels. imec's `D0=0.15 defects/cm2`, Murphy yield 0.86 for a 100 mm2
die, and line yield 0.90 reproduce only that study's assumptions.

### 14. How are mask/patterning effects modeled?

Patterning is an explicit route of lithography, deposition, etch, and clean
steps. Its electricity is either included in total fab electricity or added to
a declared non-patterning boundary exactly once. Counts are route descriptors,
not carbon coefficients. Public evidence supports qualitative EUV/DUV route
effects; exact production-node patterning carbon is not recovered.

### 15. How is mask-set NRE separated from wafer processing?

Photomask-set manufacture is amortized as
`C_maskset/(product_wafers × good_dies_per_wafer)`. It is never multiplied into
per-wafer patterning carbon. Absolute maskset carbon remains bounded/parametric;
the inverse-volume limit is tested.

### 16. What imec data were used?

Only public, source-registered material: imec.netzero v1.5.67/IEDM 2023 textual
anchors (N28 1.64 and projected A14 approximately 4.30 kWh/cm2 grid-CI
sensitivity, 0.454 kgCO2e/kWh, study-wide Scope 1/2 ranges, D0/yield/line-yield
assumptions), current lithography/process statements, SSTS direction, and the
2020 PPACE historical multipliers. No dashboard values were copied because the
numeric application required an account.

### 17. Which imec historical/current estimates are comparable?

EUV route direction is qualitatively comparable. Historical 28-to-2 nm
multipliers (3.46 electricity, 2.3 UPW, 2.5 GHG per wafer) are trend anchors,
not current coefficients. Direct-GHG trends reverse under the newer model due
to updated flows, utilization, abatement, and EUV use. Absolute estimates with
different end nodes and boundaries are not numerically compared.

### 18. How well does the model reproduce imec trends?

It reproduces the causal directions and the printed N28/A14 sensitivity
endpoints without fitting by node name. It also reproduces the mechanism by
which route-step elimination can outweigh EUV scanner energy. It does not emit
or claim a validated absolute 28/14/7/5/3/2-nm wafer-carbon curve.

### 19. How does it compare with ACT/ACT3?

An independently implemented ACT equation,
`Area(CI×EPA+GPA+MPA)/Yield`, matches the campaign's disjoint areal calculation
to floating-point precision under identical inputs. Scope-2-only N28 and A14
fixtures are 0.865767 and 2.27 kgCO2e for a 1 cm2 die at the declared yield;
they are not full die-carbon estimates. ACT3's broader BOM/component defaults
were not imported without a matched system boundary. Algebra and units are
validated; absolute magnitude is partial.

### 20. How is process-node uncertainty represented?

Intervals are propagated by a deterministic 4,096-sample Latin-hypercube
ensemble with seed 20260908 across fab CI, energy, gas use, abatement, upstream,
defect density, and line yield. The normalized good-die carbon index has median
1.1932, P05 0.6906, and P95 1.8382. These are scenario-ensemble quantiles, not
statistical confidence intervals or node-specific production distributions.

### 21. How is manufacturing maturity represented?

Labels have no numeric effect. Every scenario must explicitly provide defect
density, line yield, fab-energy, gas-use, upstream, patterning-energy, and
optional gas-abatement factors. Current ranges are parametric research
envelopes, not measurements of an early or mature fab.

### 22. What is the status of SKY130 carbon?

`SKY130_MANUFACTURING_CARBON_NOT_QUALIFIED`. The public PDK establishes a mature
180–130 nm hybrid process identity, five metal levels, mask names, and an
experimental-preview PDK status; it does not provide matched kWh/wafer or
kgCO2e/wafer. Advanced-node imec coefficients are not relabelled as SKY130.

### 23. What is measured versus translated/parametric?

SKY130 physical/macro geometry and post-route diagnostic quantities retain
measured/tool-estimate labels. imec text anchors are source-calibrated for their
advanced-node boundary. Yield, maturity, decarbonization, mask NRE, and the
uncertainty ensemble are parametric or bounded. Cross-node translation is not
presented as measurement.

### 24. What is the status of activity-qualified energy?

Unqualified. U0 maps 296/608 reported pins (48.6842%); E0 maps 142/3268
(4.3452%). E0's flattened encoder/decoder/control logic lacks a retained
RTL-to-gate name map; no matching gate VCD/SAIF or SDF/glitch activity exists.
Diagnostic power is preserved but cannot become energy/access.

### 25. What is the status of SRAM macro energy?

Tier 5, not qualified. Conditional Liberty internal-power groups and diagnostic
leakage exist, but isolated read/write validation and matched macro-boundary
activity do not. Missing macro energy does not block formula, yield, source,
or logical-control work; it blocks operational and lifecycle scores.

### 26. What is the status of Liberty uncertainty?

The upstream-original and research-corrected views are kept distinct. The
corrected view adds only characterization-consistent output transition bounds;
internal-power and timing content is byte-identical. The global 0.04 ns output
transition sensitivity is diagnostic, and the unchanged 0.351 ns `rstb`
condition remains `INSUFFICIENT_EVIDENCE`. Neither view is independent macro
energy characterization.

### 27. What is the status of bit interleaving?

I0/I1/I2 bank/address/pin mappings and inverses are executable and bijective.
I1/I2 are contracts, not placed-and-routed designs: controller area, wirelength,
energy, latency, physical bitcell mapping, and upset redistribution are absent.
Interleaving benefit remains unqualified.

### 28. What physical reliability rates are qualified?

None. Exact logical controls show all 72 E0 single-bit masks corrected, all
2,556 double-bit masks detected, and mixed DUE/SDC for logical triples and
quadruples. U0 returns SDC for its injected masks. These frequencies are not
SER/FIT/SDC/DUE event rates because physical coordinates and an upset
distribution are missing.

### 29. What lifecycle-carbon results are qualified?

No architecture-level absolute or relative lifecycle-carbon result. Wafer
accounting properties, normalized manufacturing uncertainty, yield/mask
sensitivities, and matched ACT algebra are separately qualified within their
declared boundaries.

### 30. What GREEN matrix rows are qualified?

GREEN matrix v2 contains 14 deterministic U0/E0 logical-control rows and zero
`QUALIFIED_ABSOLUTE`, zero `QUALIFIED_RELATIVE`, and zero score-bearing rows.
Each numeric diagnostic retains a row-level evidence class; unavailable values
are empty and labelled `NOT_QUALIFIED`.

### 31. What exact Pareto results exist?

Exact enumeration over minimized `GCI`, physical `SDC`, physical `DUE`, and
latency finds zero eligible rows and therefore an empty frontier. The exact
algorithm is tested on synthetic dominance/tradeoff cases. NSGA-II is not used.

### 32. Are any ECC winners scientifically defensible?

No. E0's exact logical advantages under selected injected masks do not establish
a service-per-carbon winner without event probabilities, energy, lifecycle
carbon, latency, and physical implementation evidence.

### 33. Do rankings change with technology node?

Unanswered. There is no qualified ranking at any node, so no cross-node rank
change can be reported.

### 34. Do rankings change with fab decarbonization?

Unanswered. F0–F4 independently scale Scope 1 residual, Scope 2 grid CI, and
upstream terms as declared intervals, but architecture ranking still lacks
qualified service and energy. They are scenarios, not forecasts.

### 35. Do rankings change with MBU/interleaving?

Unanswered. Logical/topological controls show why the answer can depend on
mapping, but physical bit locations, spatial upset distributions, and routed
I1/I2 costs are missing.

### 36. Do legacy and new GREEN metrics disagree?

At formula level, yes: legacy cohort normalization and arbitrary weights admit
candidate-set effects and rank reversals that GSE does not. For actual U0/E0
data, comparison is not computed because both sides lack shared qualified
inputs; no empirical disagreement or agreement is claimed.

### 37. What are the dominant uncertainty sources?

Within the declared normalized ensemble, normalized absolute Spearman influence
is: fab CI 0.3741, defect density 0.1905, abatement 0.1454, fab energy 0.0997,
line yield 0.0888, upstream 0.0535, and gas use 0.0482. This ordering depends on
chosen interval widths and is not a universal fab ranking.

### 38. What claims are suitable for ISCAS?

Suitable claims are the legacy formula counterexamples; the functional-unit
GSE/GCI definitions and properties; disjoint, evidence-labelled semiconductor
carbon accounting; deterministic bounded uncertainty; the activity-coverage
root-cause diagnosis; exact logical SECDED controls; and the explicit result
that evidence gating prevents a false winner. Parametric plots must be labelled
as such.

### 39. What claims remain unsupported?

Absolute SKY130 wafer/good-die/per-bit carbon, complete Scope 3, qualified SRAM
read/write/leakage energy, lifecycle carbon, physical SER/FIT/SDC/DUE rates,
interleaving benefit, node/decarbonization/MBU-driven rank changes, actual
legacy-vs-GSE architecture disagreement, and any GREEN/Pareto winner.

### 40. What should the next experiment be?

Run a hash-joined energy qualification campaign: simulate each exact mapped
U0/E0 final netlist with matching standard-cell models and SDF, retain a gate
VCD/SAIF or proven synthesis name map, reconcile disjoint clock/sequential/
combinational/macro/encoder/decoder/control power to the total, and independently
characterize SRAM read/write/leakage. Then add physical bitcell coordinates and
a calibrated spatial SER/MBU model, implement and route I1/I2, and obtain a
matched SKY130 fab inventory. Only the resulting joint samples should populate
GSE distributions and exact Pareto selection.

## Final classification

`GREEN_METRIC_REFOUNDED_PARTIAL_QUALIFICATION`

This classification is deliberately below `FULL_GREEN_SELECTION_QUALIFIED`.
It records a defensible framework and several qualified component findings
without converting missing evidence into a score. Historical Gate-3 remains
`FAIL`.
