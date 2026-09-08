# Gate 3 attempt 02 — pinned OpenRAM installation

## Qualified environment

Attempt 02 used OpenRAM **v1.2.48** at commit
`b6a6f12642df6b84facc24a77f9a6f67a0d62dab`. No other OpenRAM version was
used and no tutorial macro was admitted.

The compiler ran in the immutable image
`vlsida/openram-ubuntu@sha256:90ecae634f99fa9055a32e32f9d6af1acc9942b974916f114330e7b5b4b29f7c`.
The image ID is the same SHA-256 digest, its recorded size is 4,654,238,492
bytes, and it was created at 2022-06-25T22:27:31.705256261Z.

All mutable source, PDK, Python, work, output, and log paths were bind-mounted
from the F:-backed ext4 namespace
`/var/lib/green-ecc-iscas-sustainability/gate3_openram_attempt02`. Docker's
overlay store also resided inside the relocated F:-backed Ubuntu VHDX.

## Toolchain pins

| Component | Exact value |
|---|---|
| OpenRAM | v1.2.48, `b6a6f12642df6b84facc24a77f9a6f67a0d62dab` |
| Python | 3.8.10 in `/attempt/venv` |
| Magic | 8.3.311 |
| Netgen | 1.5.221 |
| ngspice | 36 |
| SKY130 technology | `sky130A`, Magic technology `1.0.291-63-ge829452` |
| open_pdks/Volare revision | `e8294524e5f67c533c5d0c3afa0bcc5b2a5fa066` |
| skywater-pdk | `f70d8ca46961ff92719d8870a18a076370b85f6c` |
| sky130_fd_pr | `f62031a1be9aefe902d6d54cddd6f59b57627436` |
| sky130_fd_sc_hd | `ac7fb61f06e6470b94e8afdf7c25268f62fbd7b1` |
| sky130 SRAM cells | `dd64256961317205343a3fd446908b42bafba388` |

The complete Python freeze is retained in
`python_requirements_attempt02.lock.txt`. Automatic conda bootstrapping was
disabled after the launcher attempted to replace the pinned image stack.

## Scientific configuration

The configuration is `openram_256x72_config.py`, SHA-256
`f8cfa843bfdc0427a6e35e620db180e2d222bd8239025eafd388379a33243fe0`.
It requests 256 words, 72 logical bits, one read/write port, one bank, a 2:1
column mux, TT/1.8 V/25 °C, SPICE characterization, DRC and LVS, and no PEX.
One spare row and one spare column satisfy the SKY130 array quanta; these do
not add a logical address, but the spare column does add a physical data bit
and `spare_wen0` to the emitted interface.

The run environment set:

```text
OPENRAM_HOME=/attempt/source/OpenRAM/compiler
OPENRAM_TECH=/attempt/source/OpenRAM/technology
PYTHONPATH=/attempt/source/OpenRAM/compiler:/attempt/source/OpenRAM/technology/sky130:/attempt/source/OpenRAM/technology/sky130/custom
PDK_ROOT=/attempt/pdk
VOLARE_HOME=/attempt/pdk/volare
SPICE_MODEL_DIR=/attempt/pdk/sky130A/libs.tech/ngspice
OPENRAM_TMP=/attempt/work/openram_tmp_256x72
```

The compiler invocation was `python3 sram_compiler.py -v
/attempt/config/openram_256x72_config.py`. `command_manifest.json` records the
complete container command.

## Attempt history

1. `launcher_bootstrap_failure_01`: the launcher attempted an unwanted conda
   bootstrap. The image Python environment was restored and pinned.
2. `geometry_constraint_failure_02`: 145 total columns violated the SKY130
   two-column quantum.
3. `geometry_constraint_failure_03`: 129 total rows violated the SKY130
   two-row quantum.
4. `run04`: completed layout generation and full verification, then exited 1.
   Magic reported 223,312 DRC violations, Netgen reported a top-level LVS
   mismatch, and SPICE characterization aborted because no `bl` alias existed
   in the timing paths.

Every failure log remains in the external attempt namespace. The decisive
run04 files were additionally copied without removing the originals to
`evidence/run04_failure/` and made read-only.
