# Calibration Measurement and Simulation Methodology

## Overview
This project stores gate-level energy calibration points in `tech_calib.json`. Each point is tied to a provenance token in `source`, and each token must resolve to a record in `reports/calibration/provenance_manifest.json`.

## Measurement/Simulation Flow
1. Select technology node and voltage point (`node_nm`, `vdd`).
2. Run the characterization flow used by the project baseline (reference simulation or sign-off measurement).
3. Record gate-level dynamic energy for:
   - `xor`
   - `and`
   - `adder_stage`
4. Capture run conditions:
   - `tempC`
   - optional `corner`
   - optional `activity_class`
5. Assign a stable provenance token (`source`) that maps to a manifest `data_sources[].id`.

## Provenance Requirements
- Every calibration entry `source` must exist in `provenance_manifest.json`.
- The manifest tracks:
  - tool versions used to generate/curate the data,
  - commit hash of the scripts/repository snapshot,
  - generation timestamp,
  - data source identifiers and human-readable descriptions.

## Validation Policy
- Runtime/default behavior: unresolved provenance emits an explicit warning (soft-fail).
- Strict behavior: unresolved provenance raises `ValueError` when strict validation is enabled.
- CI tests execute strict validation to prevent untracked provenance from merging.
