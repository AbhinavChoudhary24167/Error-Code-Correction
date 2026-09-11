# BCH timing diagnosis

BCH(78,64,t=2) is `TIMING_INFEASIBLE_AS_IMPLEMENTED` for all five inherited seeds at both constraints. Setup WNS is -11.2613 to -10.9001 ns at 10 ns (mean -11.112 ns) and -15.8314 to -15.5633 ns at 5 ns.

The compact v3.2 records do not preserve a stage-attributed critical-path report, so encoder, syndrome, error-location, correction-mux, and macro-interface contributions remain `NOT_VALIDATED`. No stage is guessed from RTL structure. BCH is retained for labelled diagnostics and excluded from the equal-performance E5 Pareto population. No pipelined replacement was introduced.
