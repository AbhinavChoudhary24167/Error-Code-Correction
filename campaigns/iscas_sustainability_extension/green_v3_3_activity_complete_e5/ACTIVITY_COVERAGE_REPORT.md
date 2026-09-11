# Activity annotation coverage

Forty-six operation records passed the logic-only E5 gates. Functional-logic exact annotation coverage ranges from `99.298390%` to `99.356061%`; combinational coverage is at least `99.235547%` and sequential coverage is at least `100.000000%`. Each qualified record identified all 72 SRAM-output root candidates.

The activity boundary is zero-delay simulation of the final routed gate netlist, recorded as VCD, with the final SPEF loaded for power analysis. Native `read_vcd` resolved top ports; exact scalar routed-net activity supplemented leaf pins. For macro-output-driven cones, a power-process-only OpenDB adapter made the VCD-measured SRAM outputs timing-graph roots. The original ODB was not modified.

SRAM macro-interface coverage is reported separately and macro-internal state activity remains unavailable. Therefore the admitted quantity is ECC-logic energy excluding macro internal energy, never unrestricted whole-memory energy.
