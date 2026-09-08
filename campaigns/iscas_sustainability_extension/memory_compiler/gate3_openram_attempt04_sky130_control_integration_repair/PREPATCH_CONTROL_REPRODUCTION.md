# Pre-patch control reproduction

The byte-identical Attempt03 16×8 configuration reproduced the prior failure under the pinned toolchain. OpenRAM exited 1. Magic reported 2,140 DRC error tiles. Netgen reported LVS failure. Characterization subsequently reached the known, out-of-scope local `nom_corner` exception; no characterization repair was attempted.

## Fixed inputs

- Configuration: `configs/control_8x16_config.py`, 1,146 bytes, SHA-256 `dc22607f0f35e401fade14046b8089cfb3f04f9db1db84bb6e24c09f9fb82fd6`.
- OpenRAM: v1.2.48, commit `b6a6f12642df6b84facc24a77f9a6f67a0d62dab`.
- Installed PDK: open_pdks/volare `e8294524e5f67c533c5d0c3afa0bcc5b2a5fa066`; SRAM cells `dd64256961317205343a3fd446908b42bafba388`.
- Container: `vlsida/openram-ubuntu@sha256:90ecae634f99fa9055a32e32f9d6af1acc9942b974916f114330e7b5b4b29f7c`.
- DRC and LVS remained enabled. No waiver, masking, black-box substitution, or deck edit was used.

## DRC result

The scalar OpenRAM/Magic result was 2,140 error tiles. The diagnostic rule-occurrence total was 7,145 because a single error tile can carry several rule messages. Dominant families were `via.1a + 2*via.4a` (1,080), `li.c2` (1,080), `li.3` (900), `li.6` (900), `via.5a - via.4a` (540), `li.c1` (535), `poly.5` (495), `licon.1` (352), `li.5` (291), `li.1` (289), `licon.5a` (281), and `mcon.1` (225). The complete histogram is in the companion JSON and raw diagnostic log.

Hierarchy bisection reproduced nonzero violations in leaf SRAM views: main/replica/dummy bitcells (8 tiles), `colend`/`colenda` (7), corners (5), row ends (7), and wordline straps (12–58 depending on variant). Replication produced 360 tiles in the main array, 380 in each replica/capped array, 252 in the replica column, and 383 at the bank level.

## LVS result

Top-level device counts matched exactly (1,802 extracted and 1,802 schematic) while net counts did not (658 extracted and 698 schematic). The bank was 1,786/1,786 devices and 643/665 nets. Leaf evidence begins in the imported SRAM views: `colend`/`colenda` expose disconnected data/supply pins plus `m2_0_4#` and `m2_0_236#` proxy pins; replica bitcells split `WL` into an extra extracted net (9 versus 8); main bitcells likewise have 10 versus 9 nets. A separate generated `pnand2_0` mismatch has 4/4 devices and 7/6 nets due to a well/bulk partition.

Raw GDS, schematic and extracted SPICE, Magic output, Netgen reports, extraction output, and the primitive matrix are preserved below `raw/`.
