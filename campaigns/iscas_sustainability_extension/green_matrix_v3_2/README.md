# GREEN Matrix v3.2 — evidence-aware cross-layer decision model

This additive campaign consumes the frozen GREEN Matrix v3.1 physical
population at `1f6bcd009e7a05ebcde35a3272161a9a81ec7bf7`. It does not edit,
reinterpret, or promote v3.0/v3.1 evidence.

The implementation refounds GREEN as:

```text
Evidence -> Qualification -> Conditional Model -> Decision
```

The primary architecture/scenario object is the evidence-bearing vector
`G(a,s) = [reliability consequence, operational resource consequence, physical
implementation cost, lifecycle consequence, evidence quality]`. It is not
collapsed into a default score. `M_E` stores evidence semantics, `M_P` stores
implementation quantities with `M_E` references, and `M_S` returns a decision
state and complete blocking set.

The campaign establishes exact conditional logical response surfaces and
declared-scenario trade-space analysis for U0/E0. It does not establish a
physical event distribution, absolute SDC/DUE/FIT, E5 energy, routed I1/I2,
Qcrit, SKY130 manufacturing/lifecycle carbon, CSCI/MRCC, a qualified
sustainability front, or a global winner.

The sustainability framing is methodologically informed by publicly available
imec SSTS/imec.netzero bottom-up concepts. No certification, compliance,
validation, standardization, or endorsement by imec is claimed, and no public
imec datum is treated as SKY130 manufacturing evidence.

See `REPRODUCE.md` for deterministic regeneration and `FINAL_REPORT.md` for the
scientific result.
