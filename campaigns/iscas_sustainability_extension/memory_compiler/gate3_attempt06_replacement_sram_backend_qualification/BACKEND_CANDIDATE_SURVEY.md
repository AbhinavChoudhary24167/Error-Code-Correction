# Attempt06 backend candidate survey

Reconnaissance followed the mandated order. Candidate A was fully inspected first. Its exact views are sufficient to run qualification, but the result is partial; therefore Candidate B and then Candidate C were investigated only at reconnaissance depth.

| Candidate | Frozen source | License / technology | Relevant dimensions | Published views | Disposition |
|---|---|---|---|---|---|
| A — SRAM22 | `ucb-substrate/sram22_sky130_macros@75cbe961e18ee00d5a6c73fa455505f0bcdf4c05` | BSD-3-Clause / SKY130 | exact 256×64 and 256×8 | GDS, LEF, SPICE, Liberty FF/TT/SS, Verilog | selected, partially qualified |
| B — GF180 MCU SRAM | `google/globalfoundries-pdk-ip-gf180mcu_fd_ip_sram@9c411928870ce15226228fa52ddb6ecc0ea4ffbe` | Apache-2.0 / GF180MCU | 64/128/256/512 × 8 only | GDS, LEF, CDL, Liberty, Verilog | not selected; no 256×64 and banking would change the baseline |
| C — FreePDK45 control | `VLSIDA/OpenRAM@b6a6f12642df6b84facc24a77f9a6f67a0d62dab` (`1.2.48`) | BSD-3-Clause / educational FreePDK45 | configurable | generatable, not pre-frozen here | non-fabricable control only; not executed |

Candidate A is reproducible for immutable view consumption but not for public foundry signoff reproduction. Its separate generator depends on a slightly modified SKY130 PDK and proprietary verification/characterization steps. Candidate B is a credible open macro library for a future GF180-specific campaign, not a drop-in replacement for this exact architecture. Candidate C cannot be represented as fabrication evidence.

No selection was based on GDS existence alone. The machine-readable survey records every requested field and the qualification limits.

