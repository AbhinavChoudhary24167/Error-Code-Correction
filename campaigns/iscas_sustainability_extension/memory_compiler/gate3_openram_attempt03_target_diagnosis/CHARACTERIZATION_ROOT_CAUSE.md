# Characterization root-cause analysis

## What searches for `bl`

During `sram.save`, OpenRAM selects a probe address and data bit, then the SPICE characterizer builds a timing graph. `compiler/characterizer/simulation.py:simulation.create_graph` excludes all bitcells except the probed row/column. `simulation.get_bl_name` constructs a technology bitcell and asks `get_alias_in_path` to find an alias of its `bl` or `br` pin in the clock-to-data timing paths.

The lookup is a graph-path alias search, not merely a string search over the generated SPICE text. It succeeds only if a retained bitcell on the timing path contributes the expected leaf `bl`/`br` alias.

## Exact attempt02 failure

Because a spare row enlarged `addr_size` to nine, `compiler/sram.py` produced probe address `"0" + "1" * (addr_size - 1)`, or `011111111`. In `simulation.get_data`, the leading one-bit column address is `0`, so probing output bit 71 at 2:1 muxing selects physical bitline column 142. In `simulation.get_row`, the remaining eight bits are interpreted as row 255.

The generated array has rows 0 through 128. `bitcell_array.graph_exclude_bits` iterates the real array and excludes every bitcell that is not exactly row 255/column 142. Since row 255 does not exist, every bitcell is excluded. The graph then contains no retained clock-to-output path carrying a leaf-bitcell `bl` alias, and `get_alias_in_path` raises `Could not find bl net in timing paths.`

The expected bitline is not absent from the netlist. The generated bank SPICE contains `bl_0_0` through `bl_0_144`, an internal spare bitline `sparebl_0`, and replica-bitline nets. It is present hierarchically under the bank, but it is absent from the filtered timing graph because the invalid probe row excluded all candidate cells.

The defect is triggered by the spare-row address expansion interacting with the probe-address construction and column-mux address ordering. It is not caused by 72 data bits alone. The 16x8 control has no column-select bit and derives valid probe row 15; its characterizer successfully resolved `xsky130_sram_1rw_8x16_gate3a03_control.xbank0.bl_0_7`.

## Separate control Liberty failure

After resolving the control bitline, Liberty characterization failed in corner setup with `UnboundLocalError: local variable 'nom_corner' referenced before assignment`. Both attempt02 and control configurations set `nominal_corner_only=True` and `only_use_config_corners=True`. OpenRAM warns that nominal-corner mode is ignored when configuration corners are supplied, but the later code path still references `nom_corner`. This is a local configuration trigger exposing an OpenRAM characterizer error path; it does not convert the control to a pass.

## Classification

- **E. CHARACTERIZER_LIMITATION**: probe-address construction does not account for the spare-row-expanded row address, so the timing graph can be emptied; the corner path also dereferences an unbound local.
- **C. TARGET_CONFIGURATION_LIMITATION**: the attempt02 combination of a spare row and 2:1 column mux triggers the invalid row interpretation.
- **G. LOCAL_CONFIGURATION_ERROR**: the simultaneous corner flags are incompatible and trigger the later control failure.

No characterizer source was patched and no error was suppressed.

