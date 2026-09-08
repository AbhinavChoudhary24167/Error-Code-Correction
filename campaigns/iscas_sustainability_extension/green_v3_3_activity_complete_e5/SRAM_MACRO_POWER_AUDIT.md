# SRAM22 macro-power audit

The two inherited tt/25 C/1.80 V Liberty views were inspected by hash. Both contain leakage, memory/timing groups, and eight CE/WE-conditioned internal-power groups. They do not establish address-dependent or data-dependent macro-internal energy, and full state-dependent coverage has not been validated.

| Quantity | Classification |
|---|---|
| leakage | `AVAILABLE` |
| internal_read_power | `PARTIAL` |
| internal_write_power | `PARTIAL` |
| clock_control_transitions | `PARTIAL` |
| address_dependent_transitions | `ABSENT` |
| data_dependent_transitions | `ABSENT` |
| output_switching | `PARTIAL` |
| read_write_timing_arcs | `AVAILABLE` |
| state_dependent_internal_power | `PARTIAL` |

Whole-memory E5 is therefore not qualified. The allowed boundary is `E5_LOGIC_ACTIVITY_QUALIFIED_MACRO_ENERGY_INCOMPLETE` if logic activity later passes its own gates; ECC-logic and whole-memory energy must remain separate.
