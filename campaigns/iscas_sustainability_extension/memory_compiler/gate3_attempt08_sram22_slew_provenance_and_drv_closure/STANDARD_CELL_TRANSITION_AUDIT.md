# SKY130HD standard-cell transition audit

The preserved SKY130HD TT library declares `default_max_transition : 1.5000000000`; affected `sky130_fd_sc_hd__xnor2_1`, `sky130_fd_sc_hd__xnor3_1`, and `sky130_fd_sc_hd__xor2_1` pins do not create the 0.60 ns limit. The common top-level SDC does: `set_max_transition 0.60 [current_design]`.

On net `_055_`, `_513_/Y` drives `_518_/A` and `_540_/A` (fanout 2). Exact extracted STA gives a worst rising transition of 0.646700442 ns at the driver and 0.646702707/0.646722376 ns at the sinks, about 0.0467 ns above the top-level rule. This is one genuine Class-A electrical net represented by three report rows. Replacing only the legal driver `xnor2_1` with `xnor2_2` gives 0.394375741 ns in the non-persistent candidate experiment and removes all three rows in final route.
