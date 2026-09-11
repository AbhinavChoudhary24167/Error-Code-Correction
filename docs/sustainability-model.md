# Sustainability model

GREEN keeps energy evidence and carbon translation separate.

For operation class `j`, count `N_j`, and qualified energy `E_j` in joules:

```text
E_use [J] = sum_j N_j * E_j
C_use [kgCO2e] = (E_use / 3.6e6) * I_use
```

where `I_use` is use-phase grid intensity in kgCO2e/kWh. `N_j` is a workload/scenario parameter. Missing macro energy makes whole-memory `E_use` and `C_use` incomplete; it is not replaced with zero.

A lifecycle study may be organized as

```text
C_lifecycle = C_manufacturing_allocated + C_packaging + C_use + C_replacements + C_end_of_life
```

Each term requires a declared functional unit and boundary. Manufacturing allocation can depend on wafer processing emissions, die area, gross dies, yield, redundancy, test/packaging allocation, and technology-specific inventory. Node scaling is not a valid substitute for a qualified inventory.

## Current evidence boundary

| Quantity | State |
|---|---|
| E5 post-route ECC-logic operation energy | Qualified for the bound SECDED/Hsiao logic windows |
| SRAM macro-internal energy | Incomplete |
| Use-grid intensity | Explicit scenario/model parameter |
| SKY130 manufacturing inventory, yield, and allocation | Blocked |
| Whole-memory operational carbon | Blocked by macro energy |
| Absolute lifecycle carbon and global sustainability Pareto front | Blocked |

The methodology is informed by public semiconductor sustainability work, including imec methodology and net-zero discussions. This repository does not assert imec certification, endorsement, compliance, or an independently verified lifecycle assessment.

Sensitivity analysis should vary workload, grid, lifetime, yield, allocation, and replacement assumptions independently and report when ordering changes. Scenario robustness does not upgrade the evidence tier of its inputs.
