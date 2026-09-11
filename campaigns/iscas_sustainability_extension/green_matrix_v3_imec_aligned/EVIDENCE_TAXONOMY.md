# Evidence taxonomy

| Tier | Meaning |
|---|---|
| E0 | Absent; the blocking reason is mandatory. |
| E1 | Assumed or exploratory parametric input. |
| E2 | Published literature or external model in its native boundary. |
| E3 | Analytical, exact logical enumeration, or RTL-derived result. |
| E4 | Synthesis or place-and-route tool estimate. |
| E5 | Activity-qualified, matched post-route result. |
| E6 | Independently cross-validated characterization. |
| E7 | Silicon or manufacturing measurement. |

Tier order is not a universal quality score.  An E7 measurement from the wrong
technology, workload, PVT, or system boundary may be unusable, while an E2
published model can be appropriate for a declared parametric study.  Every
qualification rule also checks result class and boundary relevance.

Result classes are `ABSOLUTE_QUALIFIED`, `RELATIVE_QUALIFIED`, `PARAMETRIC`,
`BOUNDED`, `DIAGNOSTIC`, `LOGICAL_CONTROL`, and `UNQUALIFIED`.  Missing evidence
does not globally invalidate other quantities.

The initial population deliberately classifies observed macro area and tool
power as diagnostics, logical enumeration as logical control, and physical
rates, qualified operational energy/latency, SKY130 manufacturing carbon, and
lifecycle metrics as E0.
