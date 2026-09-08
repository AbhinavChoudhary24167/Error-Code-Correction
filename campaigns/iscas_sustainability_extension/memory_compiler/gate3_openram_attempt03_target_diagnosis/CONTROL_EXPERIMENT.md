# Pinned-toolchain control experiment

## Selection

The control is `sky130_sram_1rw_8x16_gate3a03_control`: 16 words by 8 data bits, one 1RW port, one bank, one spare row, and one spare column. It uses the geometry of OpenRAM's shipped SKY130 `sky130_sram_1rw_tiny` example rather than an invented size. The compiler selected `words_per_row=1`. The experiment retained the exact attempt02 OpenRAM commit, container, SKY130 installation, Magic, Netgen, ngspice, TT/1.8 V/25 C corner, and full DRC/LVS/SPICE-characterization requirements.

The only new input was the separately namespaced control configuration, classified as upstream configuration and hashed as SHA-256 `dc22607f0f35e401fade14046b8089cfb3f04f9db1db84bb6e24c09f9fb82fd6`. No OpenRAM source, PDK data, verification deck, or comparison criterion was changed.

## Derived control geometry

- Logical organization: 16x8.
- Compiler-selected words per row: 1.
- Regular rows: 16; rows including one spare: 17; physical rows including the replica/dummy row: 18.
- Regular data columns: 8; columns including the spare: 9; physical columns including the replica-bitline column: 10.
- Row address bits: `ceil(log2(17))=5`; column-select bits: 0; emitted address indices: `0..4`.
- Emitted data indices: `0..8`; repair control: `spare_wen0`.

## Full-flow result

The final compiler process exited 1. Magic DRC failed with 2,140 scalar error tiles. Netgen LVS failed. GDS, SPICE, and LEF files were generated but are unqualified because physical verification failed. Liberty generation failed and no usable Liberty was produced. Verilog emission was not reached, so no usable Verilog was produced.

The characterizer did resolve a real bank bitline, `xsky130_sram_1rw_8x16_gate3a03_control.xbank0.bl_0_7`. It then failed during Liberty corner selection with `UnboundLocalError: local variable 'nom_corner' referenced before assignment`. The configuration simultaneously set `nominal_corner_only=True` and `only_use_config_corners=True`; OpenRAM warned that the nominal corner is ignored when configuration corners are used, then entered code that still expected `nom_corner`.

## Classification and boundary

`CONTROL_FAIL`.

This exact pinned OpenRAM/SKY130 integration cannot generate even its shipped tiny geometry as a fully qualified SRAM under the required flow. Accordingly, attempt03 did not run dimensional bisection. The attempt02 256x72 DRC/LVS failure cannot be attributed specifically to width or depth. The control does show that the attempt02 `bl` lookup failure is target/topology-sensitive: the control found a valid bitline before encountering the separate corner-selection defect.

