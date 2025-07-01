2025-07-02 — Instrumented SEC-DAEC with XOR/AND telemetry; average read energy ≈ 15 pJ @ 1.0 V.

The `Telemetry` struct counts XOR and AND gate evaluations inside the
`SecDaec64` decoder.  Each clean read increments the counters by the number of
parity checks (seven Hamming bits plus overall parity).  `estimate_energy()`
converts these counts to joules using `ENERGY_PER_XOR` and `ENERGY_PER_AND`
constants defined in `energy_model.py`.
