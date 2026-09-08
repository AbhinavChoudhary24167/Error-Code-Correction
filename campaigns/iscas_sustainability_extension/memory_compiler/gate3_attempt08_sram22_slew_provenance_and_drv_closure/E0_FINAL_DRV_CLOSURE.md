# E0 final DRV closure

Canonical seed 11 completed final ODB/DEF/GDS/SPEF with setup 0, hold 0, integration DRC 0, capacitance 0, antenna 0, and unconstrained endpoints 0. Setup WNS/TNS is 0.584552/0 ns and worst hold slack is 0.00122125 ns.

The accepted repairs remove every ordinary standard-cell row and both long-route `din[56:57]` rows, reducing slew 80 -> 75. The residual distribution is B2/C72/E1: data `rstb`, ECC `rstb`, all 72 macro outputs, and the data-macro clock input. Because the clock and two input rows violate explicit 0.351 ns macro-input rules and lie outside the characterized input axis, E0 is neither fully clean nor provenance-limited-only.
