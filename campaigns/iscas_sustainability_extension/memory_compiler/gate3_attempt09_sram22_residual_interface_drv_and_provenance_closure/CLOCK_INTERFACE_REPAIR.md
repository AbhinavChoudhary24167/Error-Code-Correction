# Clock-interface repair

Attempt08's data-SRAM clock endpoint was driven by `clkbuf_1_1__f_clk/X` (`sky130_fd_sc_hd__clkbuf_16`) at 0.511382282/0.351 ns, fanout 1, extracted D_NET capacitance 0.00726447 pF, and 64.28 um routed wire. This is a legitimate explicit macro clock-input rule and characterization-axis ceiling.

The phase-preserving `clkinv_8` pair produced 0.528128028 ns and failed. The smallest closing clock-cell pair was two `sky130_fd_sc_hd__clkinv_16` stages at 0.319176137 ns in the placement diagnostic. The production ECO applies that pair to the data branch and an identical pair to the ECC branch to preserve polarity and avoid unbalanced clock semantics. Canonical final data/ECC clock slew is 0.325266629/0.135259956 ns, each against 0.351 ns.

Propagated clocks, timing checks, 10 ns period, 0.10 ns uncertainty, and the SRAM input rule remain enabled. Final canonical setup/hold are 0/0 violations, route DRC and antenna are 0/0, and max capacitance is 0.
