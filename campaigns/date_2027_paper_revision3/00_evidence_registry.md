# Revision-3 numerical evidence registry

No manuscript result is sourced from an older PDF. JSON paths below are relative to the named authoritative file. Display rounding is performed by `paper/date2027_revision3/scripts/build_revision3.py`; full precision remains in the source evidence.

| Expected manuscript claim | Authoritative source | Machine-readable field |
|---|---|---|
| Matched seeds are 11, 13, 17, 19, 23 | `docs/date2027/revision2/REV2_MULTI_SEED_ENVIRONMENT.json` | `experimental_factor.values` |
| Common 10 ns technology, corner, voltage, temperature, utilization, density, margin, load | same | `technology.*`, `flow.*` |
| SECDED request latency 1 vs 3 cycles; II=1 | `docs/date2027/revision2/results/REV2_SECDED_PAIRED_SEED_EFFECTS.json` and frozen environment | `latency.*`, `power.initiation_interval_cycles` |
| SECDED exact-equivalent temporal pair, 10 ns area effect | `docs/date2027/revision2/results/REV2_MANUSCRIPT_EVIDENCE.json` | `secded_paired.effects.area_percent.summary` |
| SECDED 10 ns detailed-wire effect | same | `secded_paired.effects.detailed_wirelength_percent.summary` |
| SECDED 10 ns slack-derived-frequency effect | same | `secded_paired.effects.slack_derived_frequency_percent.summary` |
| SECDED 10 ns total-power and energy effects | same | `secded_paired.effects.total_power_percent.summary`, `achievable_energy_percent.summary` |
| SECDED 10 ns ordering counts and feasibility | same | `secded_paired.robustness.*` |
| SECDED 10 ns aggregate/per-seed Pareto relation | same | `secded_paired.dominance.*` |
| Hsiao implementation IDs, zero alignment, latency 1, II=1 | `campaigns/date_2027_breadth_remediation/formal/results/A_formal_qualification.json` | top-level identity/latency fields |
| Arbitrary-word SAT and registered-boundary temporal-induction PASS | same | `proofs.decoder_arbitrary_word`, `proofs.registered_boundary` |
| Mapped Hsiao cells 1244 vs 1254, registers 349 vs 349, XOR/XNOR 350 vs 343 | `campaigns/date_2027_breadth_remediation/synthesis/A_synthesis_structural_comparison.json` | `baseline.*`, `new_hierarchical.*`, `differences.*` |
| Hsiao mapped logic depth is NOT ASSESSABLE | same | `baseline.logic_depth_no_flip_flops`, `new_hierarchical.logic_depth_no_flip_flops` plus campaign report |
| Hsiao structural area effect and 5/5 lower ordering | `campaigns/date_2027_breadth_remediation/analysis/A_structural_pair_summary.json` | `paired_effects.standard_cell_instance_area_um2` |
| Hsiao structural cell-count effect and 5/5 higher ordering | same | `paired_effects.cell_count` |
| Hsiao structural wire and via effects, both 5/5 higher | same | `paired_effects.detailed_route_wirelength_um`, `paired_effects.via_count` |
| Hsiao structural timing effect, higher 4/5 | same | `paired_effects.slack_derived_frequency_mhz` |
| Hsiao structural power/energy effect, higher 5/5 | same | `paired_effects.total_power_w`, `paired_effects.energy_per_op_pj` |
| Algorithmic Hsiao absolute 10 ns area, frequency, wire, energy and 5/5 feasibility | `docs/date2027/revision2/results/REV2_MANUSCRIPT_EVIDENCE.json` | `architectures.hsiao_algorithmic.*` |
| SECDED mean internal, switching, leakage, total power and energy for both identities | `campaigns/date_2027_breadth_remediation/analysis/B_power_components_summary.json` | `architecture_summary.secded_comb.*`, `.secded_pipe.*` |
| SECDED paired internal +6.77%, switching -49.48%, leakage +34.43%, total/energy -23.42% | same | `paired_effects.<component>.percent_effect` |
| Combinational-group -55.50%, sequential-group +70.86%, clock-group +74.34% | same | `paired_effects.<group>_total_power_w.percent_effect` |
| Switching is largest absolute mean top-level contributor | same | `primary_component_by_absolute_mean_difference`, `mean_top_level_component_differences_w` |
| Glitch suppression is hypothesis only | same | `activity_analysis.glitch_suppression_claim`, `activity_analysis.reason` |
| 5 ns differs principally by 10 ns to 5 ns target and retains common physical controls | `campaigns/date_2027_breadth_remediation/physical/contract_v1.json` | `technology`, `common_flow`, `architectures.C_*` |
| All ten 5 ns runs route complete, DRC/hold/setup clean and power eligible; both designs 5/5 feasible | `campaigns/date_2027_breadth_remediation/analysis/C_5ns_summary.json` | `architectures_5ns.*` |
| 5 ns SECDED area, cells, wire, vias, frequency, power, energy paired effects | same | `within_5ns_paired_effects.*.percent_effect` |
| 5 ns request latency 1 vs 3, II=1 | same and frozen contract | `request_latency.*`, `physical/contract_v1.json` architecture fields |
| 10 ns to 5 ns energy: comb about -5.48%, pipe about -0.45% | same | `condition_sensitivity_percent.C_secded_{comb,pipe}.energy_per_op_pj` |
| 10 ns to 5 ns total power: comb about +89%, pipe about +99% | same | `condition_sensitivity_percent.C_secded_{comb,pipe}.total_power_w` |
| Area/timing/power/energy ordering preserved 5/5 across constraints | same | `architecture_ordering_preservation.*` |
| BCH 10 ns feasibility 0/5, area, frequency, wire, slack and 66 setup violations | `docs/date2027/revision2/results/REV2_MANUSCRIPT_EVIDENCE.json` | `architectures.bch78.*`, `bch_10ns_feasibility` |
| BCH guarantee is W1/W2 correction | qualified code/implementation records summarized in Revision-2 registry | architecture identity and qualification records |
| Historical evidence remains unchanged | `campaigns/date_2027_breadth_remediation/FINAL_baseline_integrity_check.json` | zero changed/missing/added protected paths |

