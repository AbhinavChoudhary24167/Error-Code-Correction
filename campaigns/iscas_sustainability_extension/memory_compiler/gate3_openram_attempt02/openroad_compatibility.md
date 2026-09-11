# Gate 3 attempt 02 — OpenROAD/OpenSTA compatibility

## Result

**NOT_ASSESSABLE for OpenROAD/OpenSTA macro import.** The run did not emit the
three views required for the intended lightweight qualification:

- LEF for OpenROAD macro geometry and pins;
- Liberty for OpenSTA timing and power parsing;
- Verilog for the logical module/interface.

Running `read_lef`, `read_liberty`, or `read_verilog` without those compiler
outputs would test an invented replacement rather than the generated macro.
No replacement or hand-written stub was admitted.

## Intended parser environment

The cached tool image is pinned as
`openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e`.
Read-only version probes returned:

| Tool | Version |
|---|---|
| OpenROAD | `26Q3-1080-gab6fd26351` |
| OpenSTA | `3.1.0` |

The executables are
`/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad` and
`/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta` inside that image.

## Checks completed

| Check | Status | Evidence |
|---|---|---|
| GDS top-cell parse | PASS_WITH_DIAGNOSTICS | Pinned Magic read top `sky130_sram_1rw_72x256_gate3a02` and a 562.300 × 311.195 µm full-layout boundary, while also reporting unknown SRAM-library layer/datatypes. |
| LEF parser | NOT_ASSESSABLE | No generated LEF exists. |
| Liberty parser | NOT_ASSESSABLE | No generated Liberty exists. |
| Verilog parser/interface | NOT_ASSESSABLE | No generated Verilog exists. |
| OpenROAD macro recognition | NOT_ASSESSABLE | Requires at least a usable LEF; the GDS alone is not the macro abstract consumed by this integration flow. |
| OpenSTA timing model | NOT_ASSESSABLE | Requires a qualified Liberty view. |

## Disposition

The macro is not usable by the intended OpenROAD/OpenSTA integration flow.
This is a Gate-3 failure, not permission to start SRAM+ECC placement. Gate 4
must remain stopped until a DRC/LVS-clean macro with mutually consistent LEF,
GDS, Liberty, Verilog, and SPICE interfaces is available.
