# Gate 1 — Activity-conditioned post-route power

## Verdict

**PASS.** All 40 predeclared new W1/W2 power points are admitted and joined
to 20 immutable DATE W0 points. Every row represents 100,000 useful operations
over 1,000,100,000 ps and carries the exact ODB, SDC, SPEF, netlist, RTL, VCD,
and power-report hashes. No P&R, synthesis, W0 power, proof, or trace generation
was repeated.

## Scientific checkpoint

- SECDED pipelined versus combinational energy: W0 `-23.419005%`, W1
  `-23.415727%`, and W2 `-23.418310%` (mean of five matched seed-level
  percentage effects). The pipeline advantage survives W1 and W2 in all five
  seeds.
- Relative to W0, the absolute pipeline advantage changes by
  `-0.003278`
  percentage points under W1 and
  `-0.000695`
  percentage points under W2.
- Hsiao hierarchical versus flat energy: W0 `+1.328395%`, W1
  `+1.328735%`, and W2 `+1.327249%`. The hierarchical penalty survives
  W1 and W2 in all five seeds.
- No architecture ordering reverses in any W1 or W2 seed.
- Across all architecture/action comparisons, `switching_power` has the
  largest mean absolute percentage movement. This is an action-conditioned
  component result; it is not a glitch-suppression claim.

## Evidence boundary

The common qualified boundary retains full-precision total internal,
switching, leakage, and total power; sequential/combinational/clock group
power; and activity-annotation coverage. `report_power` advertises selected
instance reporting, but frozen W0 does not retain comparable per-instance
evidence. Per-net evidence is therefore not admitted, and no causal glitch
claim is made.

## Preserved incidents

Attempt 01 failed before OpenROAD because the trace-list value was not shell
quoted. Attempt 02 produced eight complete W1/W2 report pairs but the runner's
first reconstruction tolerance was stricter than the frozen W0 report format;
the runner was stopped after the eighth completion. Those 16 measurements were
admitted by exact report hash and OpenROAD completion marker and were not
rerun. Attempt 03 executed only the remaining 24 points and passed 12/12
invocations. All namespaces remain in the final raw-evidence manifest.

## Gate criteria

- **Inputs:** Gate-0 PASS, 20 timing-feasible frozen 10 ns routed identities,
  four frozen W1/W2 traces, and inherited W0 power.
- **Outputs:** four required CSVs, interpretation/status JSON, and a raw
  evidence manifest.
- **PASS:** all 40 new points admitted with equal useful work and complete
  matched effects — satisfied.
- **CONDITIONAL_PASS:** incomplete but comparable subset with explicit missing
  points — not used.
- **FAIL:** missing/hash-invalid inputs, unequal work, or incomplete matched
  pairs — not observed.
- **NOT_ASSESSABLE:** no usable tool or frozen physical inputs — not applicable.
