# Gate 3 attempt 02 — characterization boundary

## Result

SPICE characterization is **FAIL** for the pinned OpenRAM 1.2.48 SKY130A
256×72 target at TT, 1.8 V, and 25 °C.

OpenRAM completed layout construction, top-level Magic extraction, DRC, LVS,
and SPICE netlist writing. It then created functional stimulus and measurement
decks, selected ngspice 36, and aborted before producing a numerical
characterization result:

```text
Could not find bl net in timing paths.
```

This occurred after Magic reported 223,312 DRC violations and Netgen reported
that the extracted and schematic netlists did not match. The generated SPICE
file is therefore retained as failure evidence, not as a qualified simulation
model.

## Availability matrix

| Quantity or view | Status | Boundary |
|---|---|---|
| Access delay | **UNAVAILABLE** | No completed ngspice timing result. |
| Setup time | **UNAVAILABLE** | No Liberty table or completed timing simulation. |
| Hold time | **UNAVAILABLE** | No Liberty table or completed timing simulation. |
| Read energy/power | **UNAVAILABLE** | Stimulus exists; no accepted measurement exists. |
| Write energy/power | **UNAVAILABLE** | Stimulus exists; no accepted measurement exists. |
| Leakage | **UNAVAILABLE** | No accepted leakage measurement exists. |
| Liberty timing arcs | **UNAVAILABLE** | Liberty emission was never reached. |
| Liberty internal power | **UNAVAILABLE** | Liberty emission was never reached. |
| Functional result | **NOT_ASSESSABLE** | Characterizer aborted before a pass/fail simulation result. |
| SPICE schematic | **AVAILABLE_UNQUALIFIED** | Generated, hashed, but LVS and characterization failed. |
| GDS layout | **AVAILABLE_UNQUALIFIED** | Generated and hashed, but DRC and LVS failed. |

## Numerical admission rule

No delay, setup/hold, read/write energy, dynamic power, or leakage number is
admitted from attempt 02. No analytical value is substituted for the failed
SPICE characterization, and no value is inferred from file presence or deck
contents. Any later SRAM+ECC model would therefore require a newly qualified
macro or a transparently separate external model; attempt 02 supplies neither.
