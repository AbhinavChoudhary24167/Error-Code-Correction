# OpenRAM validation report

- Fresh regeneration status: `TIMEOUT`
- Classification: `FRESH_OPENRAM_REGENERATION_PARTIAL_RUNTIME_CUTOFF`
- DRC: `DRC_NOT_COMPLETED_BEFORE_RUNTIME_CUTOFF`
- LVS: `LVS_NOT_COMPLETED_BEFORE_RUNTIME_CUTOFF`
- Characterization: `NOT_COMPLETED`
- Failure domains: `CAMPAIGN_RUNTIME_CUTOFF`
- Fresh artifact count: `1`
- Macro geometry: `{'area_um2': 162141.2649, 'height_um': 296.235, 'source': 'OpenRAM hierarchy_layout get_bbox log record', 'width_um': 547.34}`
- Pin geometry/power-pin audit: `NOT_AVAILABLE_UNLESS_COMPLETE_LEF_IS_GENERATED`
- Timing characterization: `NOT_COMPLETED`

The target is 256 words × 72 logical stored bits, one 1RW port, one bank,
TT/1.8 V/25 °C. Historical output is not substituted for a fresh failure.
Any inherited SRAM22 macro used by ORFS is separately identified in
`OPENRAM_MACRO_MANIFEST.json` and does not establish fresh OpenRAM generation.
No DRC result is treated as an array-cell waiver unless a complete cell/layer
classification supports it.

## Fresh artifact inventory

| Role | Bytes | SHA-256 | External path |
|---|---:|---|---|
| openram_log | 34950 | `6cac43c8a7997d86d986d6f4d2459ed78cfd7a847c02b5dd56e5a48ac574e242` | `/var/lib/green-ecc-v32-matched-openram-orfs-validation/openram_fresh/output/sky130_sram_1rw_72x256_green_v32_matched/sky130_sram_1rw_72x256_green_v32_matched.log` |
