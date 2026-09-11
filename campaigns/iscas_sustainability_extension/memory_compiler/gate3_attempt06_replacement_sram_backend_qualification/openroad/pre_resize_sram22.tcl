# The immutable SRAM22 TT Liberty view assigns rstb 0.448 pF capacitance and a
# 0.351 ns max transition.  The pinned sky130hd driver set cannot reach that
# slew (best observed: 0.467 ns).  Preserve the net for integration rather than
# editing Liberty or allowing repair_design to abort; final reports retain the
# published-view violation as an explicit qualification limitation.
set rstb_net [get_nets rstb]
set rstb_cells [get_cells -of_objects [get_pins -of_objects $rstb_net]]
set_dont_touch $rstb_net
set_dont_touch $rstb_cells
