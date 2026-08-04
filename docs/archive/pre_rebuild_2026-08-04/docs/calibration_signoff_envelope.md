# Calibration Signoff Envelope

This document defines the formal signoff envelope for the technology
calibration table in `tech_calib.json`.

## Supported nodes

- 28nm
- 16nm
- 7nm

## Supported VDD envelope

- **Range:** 0.55 V to 0.85 V
- **Discrete signoff points (all nodes):** 0.55 V, 0.60 V, 0.70 V, 0.80 V, 0.85 V

## Supported temperatures and process corners

- **Temperature envelope:** -40°C to 125°C
- **Discrete temperature signoff points (all nodes):** -40°C, 25°C, 85°C, 125°C
- **Supported process corners:** `ff`, `tt`, `ss`, `ssg`

## Supported workload/activity classes

- `idle`
- `nominal`
- `compute`
- `stress`

## Notes

- Gate energy entries are provided for `xor`, `and`, and `adder_stage` at every
  supported node/VDD signoff point.
- The signoff envelope is additive and parser-compatible with existing
  calibration consumers.
