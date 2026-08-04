# Transition-aware GREEN-ECC findings

> All numerical architecture points in this example are synthetic physical-unit sensitivity inputs, not synthesized or measured SRAM results.

- Objective: `lifecycle_energy_j`
- Traces: 10
- H1 adaptation paradox: supported_in_synthetic_sensitivity (2 cases)
- H2 measurable break-even region: supported_in_synthetic_sensitivity
- H3 topology changes with trace: supported_in_synthetic_sensitivity
- H4 bounded granularity benefit: supported_in_synthetic_sensitivity
- H5 hysteresis suppresses switches: conditionally_supported_in_synthetic_sensitivity

## Joint decisions

| Trace | Architecture | Design | Policy | Total | Best fixed | Net saving |
|---|---|---|---|---:|---:|---:|
| stationary_sbu | fixed | fixed-secded | best_static | 0.0978 | 0.0978 | 0 |
| stationary_mbu | fixed | fixed-taec | best_static | 0.11436 | 0.11436 | 0 |
| one_time_sbu_to_mbu | adaptive | adaptive-shared-whole | transition_aware_dynamic_programming | 1.09628 | 1.20288 | 0.106597 |
| periodic_fault_transitions | fixed | fixed-secdaec | best_static | 0.16384 | 0.16384 | 0 |
| short_noisy_fluctuations | fixed | fixed-secded | best_static | 0.06438 | 0.06438 | 0 |
| temperature_vdd_phases | fixed | fixed-secded | best_static | 0.173762 | 0.173762 | 0 |
| changing_read_write_intensity | fixed | fixed-secded | best_static | 0.1986 | 0.1986 | 0 |
| grid_carbon_transition | fixed | fixed-secded | best_static | 0.9564 | 0.9564 | 0 |
| combined_changes | adaptive | adaptive-shared-whole | transition_aware_dynamic_programming | 0.698921 | 0.732911 | 0.0339899 |
| uncertain_transitions | fixed | fixed-secdaec | best_static | 0.32084 | 0.32084 | 0 |

## Figure takeaways

- `architecture_mode_comparison.svg`: For the selected long transition trace, adaptive-shared-whole minimizes the configured lifecycle objective.
- `scheduling_formulation.svg`: Hard feasibility is applied before lifecycle scheduling; no default scalar reliability/latency trade-off is used.
- `policy_timeline.svg`: Snapshot decisions can oscillate; transition-aware and hysteretic policies retain modes when the forecast saving cannot repay switching.
- `break_even_regime_map.svg`: Longer epochs amortize migration; increasing transition cost contracts the adaptive region.
- `topology_granularity_regime.svg`: Finer granularity helps only when reduced migration exceeds its metadata and access overhead.
- `benefit_waterfall.svg`: Net benefit is reported only after transition and allocated architecture overhead are subtracted.
- `robustness_regret.svg`: High nominal savings do not imply stable decisions; uncertainty is reported separately from nominal optimality.
- `scheduler_scalability.svg`: Measured growth follows the expected dependence on both epochs and squared mode count.

## Validation boundary

The scheduler, equations, schemas, and comparisons are executable. The default experiment is a transparent synthetic sensitivity study because no Liberty, synthesis, STA, SPICE, measured transition energy, or controller characterization is present. Threshold regions are supported; technology-specific superiority is not.
