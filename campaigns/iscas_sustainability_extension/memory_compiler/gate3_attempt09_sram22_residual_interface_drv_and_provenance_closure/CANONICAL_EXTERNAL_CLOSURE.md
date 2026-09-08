# Canonical external closure

Canonical seed 11 remains a failure because one genuine 256×64 data-macro `rstb` input violation remains in each design. Original immutable-Liberty report counts remain visible: U0 65 = 64 Class C + 1 genuine external; E0 73 = 72 Class C + 1 genuine external. Class C is separately classified `UPSTREAM_SRAM22_OUTPUT_MAX_TRANSITION_MODEL_INCONSISTENCY` / `PROVENANCE_LIMITED_NOT_EXTERNAL_INTEGRATION_DRV`; it is not counted as closed or deleted.

| Design | Setup / hold violations | Cap violations | Integration DRC | Antenna | Unconstrained | WNS / TNS (ns) | Worst hold (ns) |
|---|---:|---:|---:|---:|---:|---:|---:|
| U0 | 0 / 0 | 0 | 0 | 0 | 0 | 4.460990000 / 0.000000000 | 0.024948900 |
| E0 | 0 / 0 | 0 | 0 | 0 | 0 | 0.611109000 / 0.000000000 | 0.009414080 |

The exact residual driver, sink, slew, fanout, extracted capacitance, route length/layers, strength and original/final timing context are in `RESIDUAL_EXTERNAL_DRV_INVENTORY.json`. Classification is `RESIDUAL_SRAM_INPUT_DRV_FAIL`, not an external-closure pass.
