# Photomask-set NRE model

Physical mask-set manufacture is not wafer patterning. The optional allocation
is:

`C_mask_NRE_die = C_maskset / (N_product_wafers * N_good_dies_per_wafer)`.

The code has no default `C_maskset`. If either mask-set carbon or product volume
is absent, the result is `None`, not zero and not a guessed coefficient. This
prevents mask count from being charged once through wafer lithography steps and
again through a `k*masks` shortcut.

No credible public mask-manufacturing kgCO2e constant with a compatible
boundary was recovered. All sensitivity rows are labeled
`PARAMETRIC_UNCERTAIN`; they test the allocation equation only. A future source
must state mask type, layer count, blank and pellicle boundary, inspection and
repair, clean/rework, electricity mix, lifetime, and units before the term can
be source-calibrated.
