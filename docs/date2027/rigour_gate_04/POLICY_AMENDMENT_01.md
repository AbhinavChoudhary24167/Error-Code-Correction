# Gate 04 policy amendment 01 — ORFS ABC period invocation

The first scheduled run, `secded-comb-10ns-seed11-attempt1`, failed before synthesis. The pinned ORFS Makefile's `ABC_CLOCK_PERIOD_IN_PS` fallback parsed the frozen SDC line `set clk_period $::env(CLOCK_PERIOD)` as a literal shell expression and attempted to execute a parenthesized token.

This amendment changes only the runner invocation: it supplies `ABC_CLOCK_PERIOD_IN_PS=10000` for the frozen 10.0 ns context and `ABC_CLOCK_PERIOD_IN_PS=5000` for the frozen 5.0 ns context. The SDC continues to receive the identical `CLOCK_PERIOD` value. Candidate identities, RTL, wrappers, platform, corner, image, clocks, physical seeds, traces, fault schedules, metrics, statistical rules, scenario matrix, hypotheses, and thresholds are unchanged.

The failed attempt and its raw hash manifest remain external evidence. Its retry uses `secded-comb-10ns-seed11-attempt2`. Every later retry, if any, likewise requires a new visible attempt directory. This is an administrative compatibility correction, not a scientific-contract change and not a physical result retry under the same directory.
