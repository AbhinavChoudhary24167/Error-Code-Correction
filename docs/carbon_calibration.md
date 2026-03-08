# Carbon Calibration Model

This repository includes a calibrated carbon subsystem in `carbon_model.py` with calibration data in `carbon_calib.json`.

## Scope and precision

- **Operational carbon** is calibrated from measured/estimated energy and a grid emission factor.
- **Embodied carbon** is a **proxy-calibrated** estimate from effective area, node intensity defaults, and yield assumptions.
- These outputs are suitable for comparative design analysis, but they are **not** a full process-flow LCA.

## Model split

- **Static carbon (embodied/manufacturing proxy):**
  - `static_carbon_kgco2e = area_cm2 * fab_intensity_kgco2e_per_cm2 * yield_loss_factor`
- **Dynamic carbon (operational/use-phase):**
  - `energy_kwh = energy_joules / 3.6e6`
  - `dynamic_carbon_kgco2e = energy_kwh * grid_factor_kgco2e_per_kwh`
- **Lifetime total:**
  - `total_carbon_kgco2e = static_carbon_kgco2e + dynamic_carbon_kgco2e_lifetime`

## Calibration defaults

`carbon_calib.json` provides:

- node defaults (28/16/7nm):
  - fabrication intensity min/nominal/max
  - yield factors
  - uncertainty margin
  - `design_area_multiplier` (currently 1.0 across nodes; placeholder to keep area scaling explicit)
- grid defaults:
  - region-average factors (`global_avg`, `india`, `us`, `europe`, `brazil`, `iceland`)
  - `global_avg = 0.301` kgCO2e/kWh (region-average default)
  - scenario-only best/worst factors used for stress envelopes (not region averages)
  - provenance metadata for region and scenario factors
- lifetime defaults:
  - years and accesses per day

## Node and area assumptions transparency

When a node is not directly calibrated (for example 14nm), the model maps to the nearest calibrated node and reports:

- `requested_node_nm`
- `calibrated_node_nm`
- `node_mapping_mode` (`exact` or `nearest_calibrated`)

Area assumptions report whether area was direct input or derived from a memory-bit proxy (`area_source`, `area_proxy_used`).

## Bounds vs scenarios

`estimate_carbon_bounds(...)` returns separate concepts:

- `nominal`: nominal static/dynamic/total values
- `uncertainty`: symmetric uncertainty bounds (± margin around nominal embodied term)
- `best_case`: scenario minimums using greener grid and lower node/yield intensity assumptions
- `worst_case`: scenario maximums using dirtier grid and higher node/yield intensity assumptions

Uncertainty bounds are not equivalent to scenario best/worst envelopes.

## ECC selector integration

`ecc_selector.select(...)` supports optional carbon policies (default behavior unchanged when omitted or `None`):

- `minimum_total_carbon`
- `minimum_dynamic_carbon`
- `minimum_static_carbon`
- `balanced_carbon_energy`

With a carbon policy, candidate records include:

- `static_carbon_kgco2e`
- `dynamic_carbon_kgco2e`
- `carbon_bounds`

## CLI notes

`eccsim.py carbon` preserves legacy formatting by default.

Use `--calibrated` to emit a JSON payload containing nominal/best/worst calibrated results and score breakdown, while still including legacy values.
