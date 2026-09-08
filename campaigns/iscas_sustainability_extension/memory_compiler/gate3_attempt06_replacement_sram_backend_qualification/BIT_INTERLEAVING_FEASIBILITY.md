# Bit-interleaving feasibility

Attempt06 establishes only the following:

1. **Logical interleaving:** feasible in future wrapper logic by permuting codeword indices before the two macro interfaces. This changes logical assignment, but without a physical map it cannot prove separation of vulnerable cells.
2. **Macro/bank interleaving:** already explicit at coarse granularity: data bits `[63:0]` occupy the 256×64 macro and check bits `[71:64]` occupy the separate 256×8 macro. Additional bank-level organizations are possible only as a new, explicitly controlled architecture.
3. **Physical bitcell interleaving:** not qualified. The 256×64 name exposes mux ratio 4/write size 8 and the 256×8 name exposes mux ratio 8/write size 1; GDS hierarchy and bitline/wordline labels are observable, but upstream does not publish an authoritative logical-bit-to-bitcell coordinate/permutation map.

Address/data labels and mux factors are insufficient to prove that adjacent logical bits are or are not physically adjacent after column selection, replica structures, and internal routing. A trustworthy physical interleaving map would require generator placement/netlist mapping or independently validated extracted connectivity tied to GDS coordinates; Attempt06 has neither.

Therefore later experiments may study logical or bank permutations, but must not call them physical MBU resilience or actual bitcell interleaving without new evidence.

