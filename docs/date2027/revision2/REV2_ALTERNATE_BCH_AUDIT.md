# Revision-2 alternate BCH architecture audit

Audit date: 2026-08-25

Repository search covered RTL, registries, physical configurations, DATE evidence, and tests for `(78,64,t=2)`/`shortened-bch-78-64-t2-v1` identities.

## Outcome

`NO_ELIGIBLE_ALTERNATE_BCH_ARCHITECTURE`

The repository contains one synthesizable, correction-qualified `(78,64,t=2)` implementation identity:

- `shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1`
- RTL: `asic/rtl/bch/bch_78_64_t2_v1.sv`
- architecture: combinational syndrome/Chien decoder

The separate `shortened-bch-78-64-t2-v1-reference-decoder` registry record is a correctness/reference identity, not a second hardware architecture with a common physical transaction boundary. Other BCH records have different dimensions or correction strengths. None is eligible as an alternate `(78,64,t=2)` physical candidate under the Revision-2 schedule and identity rules.

No new BCH architecture was designed, and the qualified syndrome/Chien RTL remains unchanged.
