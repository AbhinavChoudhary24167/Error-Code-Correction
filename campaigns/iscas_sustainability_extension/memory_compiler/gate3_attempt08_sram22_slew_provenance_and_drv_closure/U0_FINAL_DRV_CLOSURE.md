# U0 final DRV closure

Canonical seed 11 completed final ODB/DEF/GDS/SPEF with setup 0, hold 0, integration DRC 0, capacitance 0, antenna 0, and unconstrained endpoints 0. Setup WNS/TNS is 4.46099/0 ns and worst hold slack is 0.0249489 ns.

The final slew count is 65: 64 Class-C data-macro outputs governed by the self-inconsistent inherited 0.04 ns macro-library rule and one genuine Class-B data-macro `rstb` at about 0.62 ns against its explicit 0.351 ns input rule/range. The strongest legitimate external substitution does not close `rstb`. U0 is therefore not externally timing/DRV clean and is not eligible for the provenance-limited exception.
