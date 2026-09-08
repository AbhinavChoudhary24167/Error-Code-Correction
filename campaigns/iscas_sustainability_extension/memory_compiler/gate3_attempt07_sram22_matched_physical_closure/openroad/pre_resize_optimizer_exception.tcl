# The immutable 256x64 TT Liberty view gives rstb 0.448008 pF capacitance and
# a 0.351 ns max-transition limit. The strongest SKY130HD driver was proven in
# Attempt06 to bottom out at 0.467 ns, causing repair_design to abort before it
# could optimize other nets. Temporarily use the common design-level 0.60 ns
# optimizer bound only for SRAM rstb pins; the published 0.351 ns constraint is
# restored immediately after the optimization stage and remains in final STA.
# OpenSTA does not support overriding set_max_transition on an instance Pin;
# this attempted path is retained as a documented negative result and is not
# sourced by the final flow.
