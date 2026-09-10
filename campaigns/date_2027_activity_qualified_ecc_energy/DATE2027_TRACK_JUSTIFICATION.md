# DATE 2027 Track Justification

## Venue and track

Design, Automation and Test in Europe (DATE) 2027, research-paper track.

## Primary topic: D9 — Low-power, energy-efficient and thermal-aware design

The central dependent variable is ECC-logic energy per operation. The paper tests whether a low-power architecture ranking produced by vectorless estimation remains valid after operation-specific switching activity is applied. Its contributions concern power-model validity, operation normalization, switching/internal-power decomposition, and energy-aware design choice. These are directly within low-power and energy-efficient digital design, making D9 the strongest primary fit.

## Secondary topic: D13 — Physical analysis and design

The conclusion depends on final routed gate netlists, extracted SPEF parasitics, timing-feasible route results, and five matched physical seeds. Physical identity is not incidental bookkeeping: it is the experimental control that permits the activity abstraction to be changed without changing the circuit. D13 is therefore the appropriate mandatory secondary topic.

## Why not neighboring topics

- D12 would overemphasize memory architecture; macro-internal energy is explicitly outside the measurement boundary.
- D15 would overemphasize reliability/test; both designs have fixed SECDED semantics and reliability is not optimized.
- A pure methodology topic would understate the substantive low-power result: the ranking reverses across activity abstractions.

## Reviewer-facing one sentence

This is a D9 energy-model-validity paper whose key control—matched final-route implementations with preserved parasitic identity—makes D13 the natural secondary topic.

