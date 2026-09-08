# Interface root-cause analysis

## 73 data pins

The extra data pin comes from configured spare-column support, not from the 72-bit ECC payload or the replica column. In `compiler/modules/sram_1bank.py:sram_1bank.add_pins`, the `din` and `dout` pin loops use `range(word_size + num_spare_cols)`. With `word_size=72` and `num_spare_cols=1`, OpenRAM emits indices `0..72`. `compiler/modules/port_data.py:port_data.add_pins` propagates the same width, and `compiler/base/verilog.py` defines `DATA_WIDTH` as `word_size + num_spare_cols`.

The additional bit is therefore a repair data bit for the spare physical column. It is not a 73rd logical ECC bit. Treating the raw macro as a 72-bit logical interface would silently misstate its ports.

## Nine address pins

The ninth address pin is caused by the combination of one configured spare row and 2:1 column muxing. `sram_config.recompute_sizes` forms 129 rows (128 logical rows plus one spare), then computes `ceil(log2(129))=8` row bits. It adds one column-select bit because `words_per_row=2`, producing nine bank address bits and top-level indices `0..8`.

Without the spare row, 128 rows would require seven row bits and the same column mux would yield eight total address bits. Replica/dummy circuitry affects the physical row multiple but is not used in the address-width formula.

## `spare_wen0`

For a single spare column, `sram_1bank.add_pins` emits scalar `spare_wen0`. Its intended function is the write enable for the spare repair column on port 0. The generated behavioral write logic in `compiler/base/verilog.py` conditionally writes memory bit 72 from `din0[72]` when that signal is asserted.

There is also a concrete cross-hierarchy defect in v1.2.48: `sram_1bank.create_spare_wen_dff` connects the internal DFF input as `spare_wen0[0]`, while the top-level pin was declared as scalar `spare_wen0`. The generated attempt02 SPICE preserves that mismatch. Netgen consequently reports the scalar top-level repair pin disconnected. This is not a license to rename the pin in attempt03; it is preserved as evidence for a later isolated source-fix experiment.

## Additional behavioral-view risk

The v1.2.48 Verilog write-loop boundaries for a spare-column configuration use normal-bit upper bound `word_size - num_spare_cols - 1`. For 72+1, that makes the normal loop end at bit 70, followed by repair bit 72, leaving bit 71 unwritten. Attempt02 never emitted a usable Verilog view, so this is a source-predicted inconsistency rather than a qualified generated-view observation. A later recovery must test it explicitly.

## Classification

- Spare-column support explains data index 72 and `spare_wen0`.
- Spare-row support plus column muxing explains address index 8.
- The SKY130 technology's two-column and two-row quanta motivated the chosen spares, but do not themselves emit the pins.
- Replica circuitry changes physical dimensions but does not explain the extra externally addressable signals.
- A scalar/vector source inconsistency explains the observed disconnected repair pin.

