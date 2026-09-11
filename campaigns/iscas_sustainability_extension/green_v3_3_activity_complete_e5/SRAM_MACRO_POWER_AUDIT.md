# SRAM22 macro-power audit

The inherited tt/25 C/1.80 V Liberty views provide leakage, timing, and partial CE/WE-conditioned internal-power information, but not sufficient address/data/state-dependent macro-internal energy. No OpenRAM rerun was launched.

| Quantity | Classification |
|---|---|
| address_dependent_transitions | `ABSENT` |
| clock_control_transitions | `PARTIAL` |
| data_dependent_transitions | `ABSENT` |
| internal_read_power | `PARTIAL` |
| internal_write_power | `PARTIAL` |
| leakage | `AVAILABLE` |
| output_switching | `PARTIAL` |
| read_write_timing_arcs | `AVAILABLE` |
| state_dependent_internal_power | `PARTIAL` |

Whole-memory E5 remains unqualified. The admitted boundary is `E5_LOGIC_ACTIVITY_QUALIFIED_MACRO_ENERGY_INCOMPLETE`.
