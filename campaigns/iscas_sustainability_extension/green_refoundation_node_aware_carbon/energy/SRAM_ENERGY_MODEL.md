# SRAM energy and Liberty evidence disposition

No decision-critical SRAM energy quantity reaches Tier 1-4. The upstream
Liberty contains conditional internal-power and leakage groups, but Attempt10
did not independently validate those groups and did not map both macro
boundaries. Read energy, write energy, and leakage therefore remain **Tier 5 /
NOT_QUALIFIED** for absolute GREEN results. Diagnostic OpenROAD power is retained
as provenance, never divided by access count or multiplied by lifetime.

This does not block the framework: `energy_accounting.py` accepts independently
supplied Tier-1/2 values, published Tier-3 intervals, or explicit Tier-4 bounds.
It propagates intervals and preserves any attributable ECC subtotal. If an
active Tier-5 term is missing, the subtotal remains visible while the total and
operational carbon remain `UNQUALIFIED`; no point value is fabricated.

## Liberty views

`UPSTREAM_ORIGINAL` remains the production-provenance baseline.
`RESEARCH_CORRECTED_DIAGNOSTIC` changes only output-pin max-transition limits;
timing and internal-power groups are byte-identical to original. In Attempt10,
the diagnostic change caused every U0 seed to abort at RSZ-0090 and changed
completed E0 mean standard-cell area by -6.752%, wirelength by +0.738%, vias by
-7.533%, and tool-estimated total power by -0.508%. Those are optimizer/model
sensitivity observations, not corrected PPA or energy evidence.

The original global 0.04 ns maximum transition conflicts with all supplied
output-transition samples. The corrected bound is characterization-consistent
only over the supplied table axes; it is not foundry validation. The independent
0.351 ns `rstb` requirement remains unchanged and **INSUFFICIENT_EVIDENCE**.

## Decision boundary

Absolute qualification requires isolated read/write workloads, known window
duration, near-complete mapped standard-cell and macro-boundary activity,
glitch-aware gate activity, conditional macro arc evaluation, PVT-appropriate
leakage, and external validation of the macro power model. A Tier-3/4 reference
must remain an interval with its technology/capacity/voltage translation stated.
No suitable public SRAM reference has been asserted here because translating an
unmatched macro would introduce unsupported precision.
