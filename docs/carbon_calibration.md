# Carbon Calibration Model

This repository now includes a calibrated carbon subsystem in `carbon_model.py` with calibration data in `carbon_calib.json`.

## Model split

- **Static carbon (embodied/manufacturing):**
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
- grid defaults:
  - region factors (`global_avg`, `india`, `us`, `europe`, `brazil`, `iceland`)
  - explicit best/worst case grid factors
- lifetime defaults:
  - years and accesses per day

## Bounds and uncertainty

`estimate_carbon_bounds(...)` returns:

- `nominal`
- `best_case`
- `worst_case`
- `assumptions`

Best-case combines lower intensity/yield penalty and greener grid. Worst-case combines higher intensity/yield penalty and dirtier grid.

## ECC selector integration

`ecc_selector.select(...)` supports optional carbon policies (default behavior unchanged):

- `minimum_total_carbon`
- `minimum_dynamic_carbon`
- `minimum_static_carbon`
- `balanced_carbon_energy`

Each candidate record now includes:

- `static_carbon_kgco2e`
- `dynamic_carbon_kgco2e`
- `carbon_bounds`

## CLI notes

`eccsim.py carbon` preserves legacy formatting by default.

Use `--calibrated` to emit a JSON payload containing nominal/best/worst calibrated results and score breakdown, while still including legacy values.
