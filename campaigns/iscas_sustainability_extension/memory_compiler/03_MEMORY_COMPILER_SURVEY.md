# Gate 2 — Memory-compiler and SRAM-macro feasibility survey

## Status

**CONDITIONAL_PASS** (survey frozen 2026-08-29).

OpenRAM 1.2.48 is selected as the primary Gate-3 implementation path. It is the only surveyed parameterized compiler with a current, documented SKY130 plug-in, user-controlled word width/depth/banking/muxing, the required physical views, and an open SPICE-characterization path. It is not yet a qualified numerical extension of the DATE results: the generated macro must first pass exact PDK/corner/view/interface/characterization checks.

SRAM22 is retained as the required independent open ecosystem, but not as a direct numerical competitor at this gate. Its nominal SKY130 and 1.8 V overlap are encouraging; however, its documented modified PDK, `sky130_fd_sc_hs` support cells, restricted mux ratios, and split open/commercial characterization boundary prevent an honest join to the DATE SKY130HD evidence until those identities are reconciled.

The machine-readable survey is [memory_compiler_matrix.csv](memory_compiler_matrix.csv). `YES`, `NO`, `PARTIAL`, `CONDITIONAL_YES`, and `NOT_ASSESSABLE` are evidence states, not inferred capabilities.

## Gate contract

### Inputs

- Frozen DATE technology identity: SKY130HD, `tt_025C_1v80`, 1.80 V, 25 °C.
- Existing 64-bit ECC payload organization and equal-useful-capacity requirement.
- Current upstream project documentation and repositories, accessed 2026-08-29.

### Outputs

- A field-complete candidate matrix with explicit incompatibilities.
- A single primary compiler selection for Gate 3.
- An independent ecosystem retained without manufacturing a numerical comparison.
- A predeclared macro-qualification checklist.

### PASS criteria

A primary and an independent compiler both expose reproducible, license-compatible, directly comparable macro generation and characterization at the same PDK revision, standard-cell/macro family, voltage, temperature, timing boundary, useful capacity, and view set.

### CONDITIONAL_PASS criteria

One scientifically viable primary compiler exists, while independent candidates are either physically incomparable or require additional qualification before numerical comparison.

### FAIL criteria

No open candidate can produce the LEF, GDS, Liberty, transistor/netlist, and behavioral views needed for a traceable SRAM+ECC experiment.

### NOT_ASSESSABLE criteria

Upstream evidence is insufficient to identify a usable candidate or evaluate the required fields.

The observed state satisfies **CONDITIONAL_PASS**: OpenRAM is viable; no independent candidate is yet admitted to the same numerical comparison set.

## Candidate assessment

### 1. OpenRAM 1.2.48 — selected primary

The [OpenRAM project](https://github.com/VLSIDA/OpenRAM) describes an open Python SRAM compiler that creates layout, netlists, timing/power models, and P&R views for open and commercial flows. The [latest listed release](https://github.com/VLSIDA/OpenRAM/releases) is v1.2.48 (`b6a6f12`). Current [setup documentation](https://github.com/VLSIDA/OpenRAM/blob/stable/docs/source/basic_setup.md) lists SKY130, FreePDK45, and SCMOS support; it explicitly says current GF180 SRAM generation is unsupported. The [configuration surface](https://github.com/VLSIDA/OpenRAM/blob/stable/compiler/options.py) exposes `num_words`, `word_size`, `num_banks`, and `words_per_row`, plus one- and two-port choices.

The [usage documentation](https://github.com/VLSIDA/OpenRAM/blob/stable/docs/source/basic_usage.md) lists GDS, SPICE, Verilog, LEF, Liberty, datasheet, log, and resolved configuration outputs. The [characterization documentation](https://github.com/VLSIDA/OpenRAM/blob/stable/docs/source/characterization.md) separates the default analytical model from `-c` SPICE characterization of delay, setup/hold, dynamic power, and leakage.

Qualification cautions are material. Current upstream [issues](https://github.com/VLSIDA/OpenRAM/issues) include SKY130 LEF/LVS concerns and a reported internal-power problem in generated SKY130 Liberty. Therefore Gate 3 must inspect the actual views and may not treat generation success as characterization correctness.

### 2. SRAM22 0.2.0 — independent SKY130 condition

The [SRAM22 project](https://github.com/ucb-substrate/sram22) is a BSD-licensed configurable generator and explicitly calls itself work in progress. Its current configuration supports `num_words`, `data_width`, `mux_ratio`, and `write_size`; mux ratio is restricted to 4 or 8, the array must have at least 16 rows and columns, and the open interpolation Liberty model accepts widths 8–128. The tool always produces tt/ss/ff Liberty by interpolation; SPICE/Liberate, PEX, DRC, and LVS require the full commercial/BWRC installation.

Its independent value is credible: the [pre-generated SKY130 macro repository](https://github.com/ucb-substrate/sram22_sky130_macros) contains a broad fixed set, identifies 21 macros that operated in shuttle silicon at 1.8 V and 25 MHz, and also states that detailed characterization is still in progress with no performance guarantee. The [Chipyard SKY130 OpenROAD tutorial](https://github.com/ucb-bar/chipyard/blob/main/docs/VLSI/Sky130-OpenROAD-Tutorial.rst) integrates these macros in an OpenROAD flow.

This is not direct-comparison permission. SRAM22 requires a slightly modified SKY130 PDK and `sky130_fd_sc_hs` support cells; its Liberty may come from interpolation or a proprietary characterization path. Those boundaries differ from the frozen DATE SKY130HD logic condition until proven otherwise.

### 3. IHP `sg13g2_sram` — fixed second-technology library

The [IHP OpenPDK](https://github.com/IHP-GmbH/IHP-Open-PDK) supplies a 130 nm SG13G2 implementation condition. Its [SRAM documentation](https://ihp-open-pdk-docs.readthedocs.io/en/latest/contents/reference_libraries/sram.html) inventories 29 fixed one- and two-port macros and delivered CDL, GDS, LEF, Liberty, Verilog, datasheet views. This is a useful Gate-10 robustness candidate, not a compiler and not numerically comparable to DATE SKY130HD.

### 4. GF180MCU fixed macros — screened external condition

The [open_pdks GF180MCU packaging documentation](https://github.com/fossi-foundation/open-pdks/blob/main/gf180mcu/README) identifies a fixed `gf180mcu_fd_sram` library with GDS, LEF, Liberty, SPICE, and Verilog views. It is not a parameterized compiler and the process/corner/voltage boundary is incompatible with the DATE condition. Current OpenRAM documentation also says GF180 SRAM generation is unsupported, so this cannot be used to claim an OpenRAM second-PDK experiment.

OpenFASoC was screened but not admitted: its current upstream scope did not provide evidence of a maintained SRAM compiler with the required views and characterization boundary. It is omitted from the numerical candidate set instead of filling capability fields by assumption.

## Comparability matrix

| Candidate | Same process family as DATE | Exact DATE PDK/library proven | 1.80 V / 25 °C exact corner proven | Equal useful capacity possible | Characterization boundary aligned | Numerical disposition |
|---|---:|---:|---:|---:|---:|---|
| OpenRAM SKY130 | Yes | Not yet | Not yet | Yes | Not yet | Gate-3 qualification target |
| SRAM22 SKY130 | Yes | No — modified PDK / HS cells | Temperature not established for generated view | Yes | No — interpolation or commercial | Separate independent condition |
| IHP SG13G2 | No | No | No | Fixed-size dependent | No | Gate-10-only condition |
| GF180MCU fixed macros | No | No | No | Fixed-size dependent | No | External condition only |

No cross-row numerical ranking is admissible from this survey.

## Gate-3 predeclared qualification

The first useful organization will be a 64-bit payload plus eight SECDED/Hsiao check bits (72 stored bits per logical word). The first bounded feasibility attempt is **256 words × 72 bits, one read/write port, one bank**, with the mux/words-per-row value selected by the compiler and then frozen. This size is experimental rather than tutorial-derived: it preserves the repository's 64-bit payload, exposes redundancy storage directly, and remains small enough for full-view generation and SPICE qualification before scaling equal useful capacity through replicated banks.

A macro is admitted only if all of the following hold:

1. compiler version/commit, configuration, PDK revision, and tool versions are frozen;
2. LEF, GDS, Liberty, SPICE, and Verilog views exist, are non-empty, and hash cleanly;
3. Liberty parses and declares the intended nominal corner, 1.80 V, and 25 °C;
4. LEF/GDS dimensions agree within representation tolerance;
5. logical interface and 256×72 organization agree across Verilog, SPICE, LEF, and Liberty;
6. DRC/LVS results are preserved when the available open toolchain supports them;
7. access time is reported separately from read energy, write energy, and leakage;
8. analytical and SPICE-derived values are never silently mixed;
9. data-SRAM, redundancy-SRAM, and ECC-logic boundaries remain non-overlapping;
10. any known Liberty internal-power defect is tested against raw characterization evidence before admission.

If full SPICE characterization or exact-corner evidence is unavailable, Gate 3 will stop at `CONDITIONAL_PASS` and will not feed fabricated energy values into Gate 6.

## Scientific decision

Proceed to a bounded OpenRAM setup and 256×72 qualification attempt. Retain SRAM22 as an independent SKY130 implementation condition, but do not spend compute generating it until the OpenRAM path has a stable view and characterization contract. IHP and GF180 remain separate-technology robustness candidates only.
