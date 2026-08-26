# Gate 07 energy-comparison audit

`ENERGY_COMPARISON_VALID`

The comparison is valid only as steady-stream energy per accepted comparison transaction at the common 10 ns constraint and II=1. It does not assert lower single-request latency: combinational SECDED has nominal latency 1 cycle and pipelined SECDED has latency 3 cycles.

| Check | Frozen result |
|---|---|
| Useful work | 100,000 accepted 64-bit comparison transactions per trace |
| Input trace | Same `conventional_secded` no-error VCD family for both physical implementations |
| Clock / duration | 10 ns; 1,000,100,000 ps for both |
| Reset / valid work / drain | 6 / 100,000 / 4 cycles for both |
| Drain sufficiency | 4 invalid cycles exceed the 3-cycle pipelined boundary latency |
| Initiation interval | 1 cycle for both; no valid-workload bubbles |
| VCD annotation | 139 directly annotated pins for both; propagation then covers implementation-specific internal activity |
| Power extraction | Post-route OpenSTA `report_power -digits 12` after VCD annotation and activity propagation |
| Energy formula | `power_W × total_time_ps / 100000 = pJ/useful operation` |

Combinational no-error power/energy are 0.01457479409873 W and 145.762515781399 pJ/op. Pipelined values are 0.01107450760901 W and 110.756150597709 pJ/op. The independently recomputed change is -24.016027025898%.

The lower pipelined value is not caused by incomplete drain, unequal operation counts, unequal trace duration, different workload, different input VCD annotation, or pipeline bubbles. Reset and drain overhead are included equally. Because total trace time and operation count are equal, the power and energy percentage changes are identical.
