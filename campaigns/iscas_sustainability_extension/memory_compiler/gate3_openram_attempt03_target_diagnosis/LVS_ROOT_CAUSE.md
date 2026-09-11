# LVS root-cause analysis

## Structural result

Attempt02 has equal device counts—154,542 schematic and 154,542 extracted—but 40,403 schematic nets versus 40,987 compared extracted nets. The 584-net excess, together with matched devices, identifies a connectivity/extraction discrepancy rather than missing or duplicated transistor generation.

Two independently evidenced mismatch layers are present.

### 1. Top-level repair-pin disconnection

The generated SPICE top-level subcircuit declares scalar `spare_wen0`. Inside the same generated view, `Xspare_wen_dff0` connects to the distinct token `spare_wen0[0]`. This is traced directly to `sram_1bank.add_pins`, which declares a scalar for one spare column, and `sram_1bank.create_spare_wen_dff`, which always indexes the signal in its loop. Netgen therefore reports one disconnected top-level pin.

This explains the repair-control disconnect, but it does not explain the repeated 584-net excess.

### 2. Replicated primitive-view connectivity mismatch

Netgen's mismatch fragments repeatedly compare schematic internal nets such as `m2_0_4#` and `m2_0_236#` against extracted proxy nets such as `proxym2_0_4#` and `proxym2_0_236#` in `sky130_fd_bd_sram__sram_sp_colend` and `sky130_fd_bd_sram__sram_sp_colenda` instances under `sky130_capped_replica_bitcell_array`.

The arithmetic is exact for the reported net-count delta: two extra extracted connectivity partitions across 146 `colend` plus 146 `colenda` instances gives `2 * (146 + 146) = 584`. Primitive replica-bitcell comparisons also show nine schematic/extracted-node positions against eight on the opposite side, with wordline/internal connections paired differently. Those primitive mismatches propagate through the repeated array hierarchy.

The repair pin is thus not a single error that fans out into every LVS mismatch. The report establishes one top-level source naming defect and a separate repeated mismatch between SKY130 schematic and extracted primitive connectivity. The tiny control also fails LVS, corroborating that the latter is a toolchain/technology-view integration failure rather than a 72-bit-only topology.

## Scientific boundary

No LVS deck, black-box rule, property, or comparison criterion was relaxed. GDS and SPICE remain unqualified. A later source/technology experiment must first make the shipped tiny control pass with the unmodified signoff comparison before the 256x72 target can be reconsidered.

## Classification

- **D. SPARE_REPAIR_CONFIGURATION_ERROR** for scalar `spare_wen0` versus internal `spare_wen0[0]`.
- **F. PDK/VERIFICATION_INTEGRATION_PROBLEM** for repeated primitive schematic/extraction connectivity partitions.
- **B. SKY130_TECH_PLUGIN_LIMITATION** as the affected views and hierarchy are SKY130-specific and reproduced by the stock-compatible control.

