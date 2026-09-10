# Claim Ledger

| ID | Manuscript claim | Evidence | Qualification | Status |
|---|---|---|---|---|
| C1 | All ten 10-ns Hamming/Hsiao physical runs route and meet setup timing. | sealed physical results; `data/physical_deltas.csv` | One flow/library/corner | VERIFIED |
| C2 | The comparison uses five matched seeds per architecture. | physical results; seed set 11,13,17,19,23 | Seeds are paired realizations | VERIFIED |
| C3 | Vectorless total logic power favors Hsiao in 5/5 pairs. | `data/vectorless_ordering.csv` | Diagnostic baseline only | VERIFIED |
| C4 | There are 46 admitted activity records and 23 matched cells. | sealed `RUN_MANIFEST.json`; reproducibility table | Idle/write seed 11 missing | VERIFIED |
| C5 | Activity-qualified energy favors Hsiao in 4/23 cells. | `data/operation_energy_deltas.csv` | ECC-logic boundary | VERIFIED |
| C6 | Clean read mean delta is -0.0308 pJ/op; Hsiao lower 3/5. | generated headline table | Descriptive, not population inference | VERIFIED |
| C7 | Write mean delta is +0.1207 pJ/op; Hsiao lower 0/4. | generated headline table | Four matched pairs | VERIFIED |
| C8 | Correction mean delta is +0.3095 pJ/op; Hsiao lower 0/5. | generated headline table | Five matched pairs | VERIFIED |
| C9 | Detection mean delta is +0.1935 pJ/op; Hsiao lower 0/5. | generated headline table | Five matched pairs | VERIFIED |
| C10 | Idle mean delta is +0.0191 pJ/window; Hsiao lower 1/4. | generated headline table | Scheduled idle operation, not residency | VERIFIED |
| C11 | Coverage is 99.298390–99.356061%, all 72 output roots, 16 warm-up cycles, 256 operations. | reproducibility table; coverage CSV | Coverage does not prove workload representativeness | VERIFIED |
| C12 | Hsiao physical mean deltas are +237.6 um2 area, +2992.8 um wire, +467.8 vias, +0.2437 ns WNS. | `data/physical_deltas.csv` | Hsiao minus conventional | VERIFIED |
| C13 | Clean-read switching decreases while internal power increases in all five pairs. | `data/component_power_deltas.csv` | Tool/library component model | VERIFIED |
| C14 | Operation-dependent internal/switching competition explains sign differences. | component decomposition | Mechanistic inference, not causal proof | INFERRED_FROM_VERIFIED_COMPONENTS |
| C15 | Architecture ordering is not invariant to the activity abstraction in this population. | C3–C10 | Conditional on implementation and models | VERIFIED_CONDITIONAL |
| C16 | Ghosh et al. is the closest verified prior activity-aware ECC checker work. | literature audit | “Closest” is an evidence-based assessment | VERIFIED_ASSESSMENT |
| C17 | Whole-memory and silicon energy are not claimed. | boundary definition; macro qualification | Explicit exclusion | VERIFIED_SCOPE |

No manuscript headline claim is sourced only from an internal campaign label. Internal labels are translated through `DATE2027_TERMINOLOGY_MAP.md`.

