# ECC architectures

GREEN distinguishes a mathematical code, a concrete encoder/decoder implementation, and its deployment architecture. Two entries with the same family name may differ in parity construction, correction policy, ambiguity handling, latency, or physical wrapper.

## Matched physical campaign

| Label | Role | Current campaign status |
|---|---|---|
| U0 | Unprotected matched baseline | Functionally validated; timing-feasible at 10 ns and 5 ns |
| SECDED | Conventional extended-Hamming 72/64 path | Functionally validated; timing-feasible at 10 ns, not 5 ns |
| HSIAO_SECDED | Hsiao-style SECDED 72/64 path | Functionally validated; timing-feasible at 10 ns, not 5 ns |
| BCH_78_64_T2 | Shortened BCH with declared `t=2` | Functionally validated; not timing-feasible at 10 ns or 5 ns as implemented |
| SEC_DAEC | Bounded adjacent-error policy candidate | Failed a preserved counterexample; excluded from physical comparison |

The general registry contains 15 code specifications and 17 implementation/deployment records, including cyclic, BCH, odd-column, synthesized Forge/SAFEForge, and archived table-decoder artifacts. List the live registry with:

```bash
python eccsim.py ecc list
python eccsim.py ecc verify --implementation hsiao-generated-combinational-72-64-v1
```

## Decoder outcomes

Consumers must use the result contract, not infer behavior from a label. A decoder may return corrected data plus status fields that distinguish no error, corrected error, detected uncorrectable error, and policy-specific ambiguity. Exact verification binds those outcomes to the declared mask universe.

## Selection boundary

Code rate, correction radius, parity/XOR structure, latency, area, routing, timing, power, and resilience are separate quantities. No architecture is globally preferred unless every required objective is compatible and qualified. The current campaign explicitly records `NO_GLOBAL_WINNER_QUALIFIED`.

See the generated [ECC catalogue](ECC_CATALOGUE.md) for record-level identities and [Adding an ECC](adding-an-ecc.md) for the extension contract.
