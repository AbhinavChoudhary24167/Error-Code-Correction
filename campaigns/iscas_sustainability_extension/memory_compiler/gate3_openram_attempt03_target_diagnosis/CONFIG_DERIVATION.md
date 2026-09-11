# Exact 256x72 OpenRAM configuration derivation

## Scope and provenance

This reconstruction is a read-only analysis of Gate-3 attempt02. It uses the unmodified `openram_256x72_config.py` (SHA-256 `f8cfa843bfdc0427a6e35e620db180e2d222bd8239025eafd388379a33243fe0`) and OpenRAM v1.2.48 at commit `b6a6f12642df6b84facc24a77f9a6f67a0d62dab`. No compiler or technology source was changed.

## Source-level derivation

The configuration supplies `word_size=72`, `num_words=256`, `num_banks=1`, `words_per_row=2`, `num_spare_rows=1`, and `num_spare_cols=1`. `compiler/sram.py:sram.__init__` passes those option values to `sram_config`. `compiler/sram_config.py:sram_config.__init__` records them, and `recompute_sizes` derives the array geometry.

For one bank:

1. Words per bank = `num_words / num_banks = 256 / 1 = 256`.
2. Logical stored bits per bank = `word_size * words_per_bank = 72 * 256 = 18,432`.
3. Regular data columns = `words_per_row * word_size = 2 * 72 = 144`.
4. Logical row count before spares = `words_per_bank / words_per_row = 256 / 2 = 128`.
5. Addressable/repair row positions in the bank = `128 + num_spare_rows = 129`.
6. SKY130's single 1RW port adds one replica/dummy row, so the physical array has `129 + 1 = 130` rows.
7. The one 1RW port contributes one replica-bitline column and the configuration adds one spare column, so the physical array has `144 + 1 + 1 = 146` columns.

Both physical dimensions satisfy the SKY130 technology quanta declared in `technology/sky130/tech/tech.py`: `array_row_multiple=2` and `array_col_multiple=2`.

The bank address sizing is not simply `ceil(log2(num_words))`. OpenRAM computes:

- `row_addr_size = ceil(log2(num_rows)) = ceil(log2(129)) = 8`;
- `col_addr_size = int(log2(words_per_row)) = int(log2(2)) = 1`;
- `bank_addr_size = row_addr_size + col_addr_size = 9`;
- with one bank, `addr_size = bank_addr_size = 9`.

Thus the ninth address bit is caused by including the spare row in `num_rows` before address sizing, together with the one column-mux select bit. It is not created by replica circuitry, and it is not required by the frozen 256-word logical address space, which requires only eight address bits.

The emitted data width is separately widened by the spare column. `compiler/modules/sram_1bank.py:sram_1bank.add_pins` loops over `word_size + num_spare_cols`, so the top-level `din0` and `dout0` indices are `0..72` (73 pins each). The same function emits scalar `spare_wen0` when there is exactly one spare column.

## Result

The logical target remains 256 words by 72 stored data bits, but this configuration requests OpenRAM's physical repair structures. In v1.2.48 those structures enlarge the externally emitted bank interface to 73 data pins, nine address pins, and `spare_wen0`. That interface is not equivalent to the frozen plain 256x72 contract and cannot be admitted without an explicit wrapper/contract decision and cross-view consistency proof.

