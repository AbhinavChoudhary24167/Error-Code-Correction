# Revision-3 claim audit

All numerical claims were regenerated from machine-readable qualified evidence by `paper/date2027_revision3/scripts/build_revision3.py`. “Supported” means the cited source hash appears in `data/claim_registry.json`; it does not broaden the stated scope.

| Manuscript claim | Evidence | Qualification / boundary | Status |
|---|---|---|---|
| ECC semantics, hardware identity, and physical identity are separate experimental objects. | Formal records, frozen RTL/environment, and route/power manifests use separate identity fields. | Methodological synthesis; no numerical universality claim. | Supported |
| SECDED combinational and pipeline RTL are exact-equivalent after two-cycle alignment. | Revision-2 formal/evidence registries. | Frozen RTL and transaction boundary only. | Supported |
| SECDED latency is 1 vs 3 cycles; both II=1. | Frozen Revision-2 environment and paired evidence. | Request latency, not memory-system access latency. | Supported |
| At 10 ns, pipeline effects are area +37.2%, detailed wire +11.2%, slack-derived frequency +46.6%, energy/op -23.4%. | `REV2_MANUSCRIPT_EVIDENCE.json`, paired summaries. | Means of five matched deterministic seeds; not population estimates. | Supported |
| Those 10 ns signs hold in 5/5 matched seeds and the pair is non-dominated. | Revision-2 robustness and dominance records. | Closed seed set and admitted objectives only. | Supported |
| Hsiao flat and hierarchical decoders have arbitrary-word decoder equality and same-cycle transaction equality. | `A_formal_qualification.json`. | Frozen pair, equal initialization, zero alignment. | Supported |
| Hsiao mapped structures are distinct: 1244 vs 1254 cells, 349 vs 349 registers, 350 vs 343 XOR/XNOR cells. | `A_synthesis_structural_comparison.json`. | One common synthesis policy. | Supported |
| Hsiao mapped combinational depth is not assessable. | Synthesis comparison records null depth for both. | No inference from timing or cell histograms. | Supported |
| Hierarchical-vs-flat Hsiao effects are area -0.564%, wire +3.867%, vias +3.918%, timing +2.656%, energy +1.328%. | `A_structural_pair_summary.json`. | Means of five matched seeds. | Supported |
| Hsiao area/wire/via/energy signs hold in 5/5; timing is higher in 4/5 and reverses once. | Structural-pair ordering counts and per-seed values. | Modest mixed effect; neither representation is declared superior. | Supported |
| The Hsiao effect is visually modest relative to the temporal effect. | Figure 2 uses the same -30% to +60% axis for both panels. | Deliberate non-exaggeration; timing reversal remains visible numerically. | Supported |
| At 10 ns, SECDED switching falls 49.48% while internal rises 6.77% and leakage rises 34.43%; total/energy falls 23.42%. | `B_power_components_summary.json`. | Mean paired component accounting. | Supported |
| Combinational-group power falls 55.50%, while sequential and clock groups rise 70.86% and 74.34%. | Same power summary. | Group totals, not per-net causal mechanism. | Supported |
| The switching decrease numerically outweighs the internal and leakage increases. | Architecture means: 7.8221 to 3.9514 mW switching; 6.7533 to 7.2104 mW internal; leakage remains nW-scale. | Accounting statement only. | Supported |
| Glitch suppression is plausible but unproven. | Power evidence explicitly marks the mechanism as not established; per-net activity was not retained. | Hypothesis, never a result claim. | Properly bounded |
| All ten 5 ns SECDED implementations are route-, DRC-, hold-, setup-, and power-eligible. | `C_5ns_summary.json`. | Two frozen identities, five seeds each. | Supported |
| At 5 ns, pipeline effects are area +36.7%, timing +68.6%, energy -19.3%; signs hold 5/5. | 5 ns within-condition paired summaries and ordering records. | Constraint robustness within the same technology/library/corner. | Supported |
| 10-to-5 ns total power rises about 89.0%/99.1% while energy changes -5.48%/-0.45% for comb/pipe. | Condition-sensitivity fields. | Power and energy kept distinct because trace duration changes. | Supported |
| The 5 ns result is not technology portability. | Frozen contract changes target/period-dependent delays while retaining technology, library, voltage, corner, and flow. | Explicit negative boundary. | Supported |
| Evaluated BCH has W1/W2 correction, 0/5 target feasibility, mean area 57240 µm², 66.6 MHz slack estimate, -5.01 ns setup slack, and 66 violations/seed. | Revision-2 qualified architecture and evidence registry. | One syndrome/Chien RTL; not a BCH-family judgment. | Supported |
| No target-clock BCH energy is claimed. | Eligibility rules and 0/5 setup feasibility. | Missing is not zero and is not inferred from derived frequency. | Supported |
| Numerical outcomes do not generalize across RTLs, flows, nodes, corners, or floorplans. | Experimental contract contains only one technology/library/corner and named identities. | Limitation statement. | Supported |

## Claim-language checks

- The timing quantity is always named a post-route signed-slack-derived frequency estimate; the manuscript explicitly says it is not measured `Fmax` or a frequency sweep.
- Deterministic seeds are described as controlled heuristic perturbations, never randomized replicas.
- BCH correction strength remains categorical; it is never folded into a scalar PPA score.
- “Exact equivalence” is attached only to the qualified pair and correct temporal alignment.
- “Glitch suppression” appears only as a hypothesis.
- Hsiao's small effect is preserved in text, table, and shared-scale figure.
