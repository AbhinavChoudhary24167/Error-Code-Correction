# GREEN-ECC physical simulation capability audit

**Study:** `green_ecc_physical_simulation`  
**Evidence label:** physically grounded simulation, not measured silicon  
**Audit date:** 2026-08-04 (Asia/Calcutta)  
**Repository revision inspected:** `985d68febae6ad17500770f76166e3781073a89f`  
**Repository version:** `ESII v0.1`  
**Stage 1 decision:** **FAIL - stop before preregistration or implementation.**

## 1. Decision

This checkout and the locally discoverable tool environment do not contain both of
the prerequisites required by the capability gate:

1. a credible transistor model/PDK with documented PVT support; and
2. a characterized digital standard-cell library suitable for synthesis, timing,
   power, and place-and-route.

No primary technology can therefore be selected. Neither option A (a legitimately
available foundry PDK) nor option B (SKY130/OpenPDK) is locally executable. The study
must stop at Stage 1. No physical-simulation preregistration, SRAM circuit deck,
physical-characterization schema, physical rerun, or proxy replacement is authorized
by the available evidence.

No tool or PDK was downloaded during this audit. No proprietary model, PDK, license
value, or library content was copied, exposed, or committed.

## 2. Audit method and scope

The audit used read-only checks of:

- commands available on `PATH`;
- common local installation roots and installed-application records;
- local MSYS2 package records;
- likely user project/download locations, to a bounded directory depth;
- repository files and contents for physical-design collateral and tool invocations;
- file metadata and hashes for the usable open RTL tools; and
- only the **names** of relevant environment variables, not their values.

The operating environment reported `Microsoft Windows 10.0.26200`. WSL is not
installed. A process-level `LM_LICENSE_FILE` variable exists, but its value was
intentionally not inspected or recorded. The presence of that variable does not prove
an entitlement to any named tool or PDK.

## 3. Installed tool audit

| Capability | Result | Version or evidence | Usability for this study |
|---|---|---|---|
| Cadence Virtuoso | Not found | No command or common installation root | Unavailable |
| Spectre | Not found | No command or common installation root | Unavailable |
| ADE Explorer/Assembler | Not found | No command or common installation root | Unavailable |
| Liberate | Not found | No command or common installation root | Unavailable |
| Genus | Not found | No command or common installation root | Unavailable |
| Innovus | Not found | No command or common installation root | Unavailable |
| Tempus | Not found | No command or common installation root | Unavailable |
| Voltus | Not found | No command or common installation root | Unavailable |
| ngspice | Not found | No executable or local package | Unavailable |
| Xyce | Not found | No executable or local package | Unavailable |
| SKY130/OpenPDK | Not found | No PDK root, package, or matching bounded-search directory | Unavailable |
| OpenRAM | Not found | No command, package, or project directory | Unavailable |
| Yosys/ABC | Found | Yosys `0.30+48`, git `b5b0b7e83` | Generic structural synthesis only |
| OpenSTA | Not found | No `sta` or `opensta` executable | Unavailable |
| OpenROAD | Not found | No executable or project directory | Unavailable |
| Verilator | Found | `5.020`, 2024-01-01 | RTL lint/simulation; no physical characterization |
| Icarus Verilog/VVP | Found | `12.0` development build | RTL simulation; installed path requires the repository portability shim |
| Vivado/Vitis | User-reported, not discoverable | User reports Vivado `2019.1`; no executable was found on `PATH`, in standard 2019.1 roots, or in the bounded search | Installation and license cannot be independently verified in this shell |
| VCD/SAIF power flow | Incomplete | RTL simulators can generate VCD when instrumented, but current ASIC testbenches contain no VCD/SAIF dump setup and no SAIF-aware power tool is available | Functional activity could be produced; characterized power cannot |

Executable hashes used to bind the audit environment:

| File | SHA-256 |
|---|---|
| `yosys.exe` | `DA2209DE850FFF3546F3FC7FB4203E62C611FDA7D5103785A1A453E16566AAA5` |
| `verilator_bin.exe` | `63E83CEAE8EE75F11E6C473802E262146583D68347D908D4568740B04819B296` |
| `iverilog.exe` | `67AD019127AF918172156EA3393CA297D61D889BB8B1EFB202FCF6E985CA6E82` |
| `vvp.exe` | `7D18C437867E2FF41C7E4B7BB2D072E5F1E2CF08794B68405A93423E52334FC0` |

## 4. PDK, model, and library audit

### 4.1 Available PDKs and licensing

No ST 65 nm, SKY130, generic Cadence PDK, OpenPDK, FreePDK, ASAP7, or other
transistor PDK was found in the repository or bounded local search. No Spectre,
SPICE, BSIM, statistical mismatch, extraction, or foundry corner decks were found.

The `LM_LICENSE_FILE` variable name is present, but no license-server value or
proprietary entitlement was captured. No Cadence executable was discoverable, so a
Cadence or ST 65 nm flow cannot be claimed available. Proprietary PDK availability is
**unverified**, not absent by assertion; it is unusable for this study until a lawful,
accessible installation is demonstrated.

### 4.2 Transistor and simulation models

| Required item | Audit result |
|---|---|
| MOS transistor model deck | Missing |
| Documented TT/SS/FF or equivalent model sections | Missing |
| Statistical process models | Missing |
| Device mismatch models | Missing |
| Monte Carlo simulator support tied to those models | Missing |
| Extracted capacitance/resistance technology | Missing |
| QRC/ICT/technology files | Missing |
| PDK-supported voltage range | Not available |
| PDK-supported temperature range | Not available |

The repository contains high-level Python/C++ Monte Carlo and uncertainty routines.
Those are synthetic system-level sampling utilities, not transistor process or
mismatch Monte Carlo and cannot satisfy the SRAM characterization requirement.

### 4.3 Standard-cell and physical implementation collateral

No characterized Liberty, LEF, GDS/OASIS, technology LEF, RC extraction deck, SPEF,
SDF, or routed DEF was found in the repository or the bounded local asset search.

Yosys ships a 2,432-byte `yosys_cells/cells.lib`-style functional library at the
installed tool path. Its inspected content defines logical cells but contains no
`area`, timing arcs, leakage power, or internal/switching power tables. Its SHA-256 is
`932FF5436ED3BEA9B692C66E34006C6490250718EAAC67526D940CDAF1B0EE51`.
It is not a characterized standard-cell library and cannot support area, timing,
leakage, dynamic-power, PVT, or routed claims.

Consequently, there are no usable digital process corners, characterized voltage or
temperature points, wire-load/parasitic corners, or place-and-route technology rules.

## 5. SRAM collateral audit

The repository contains synthesizable behavioral SRAM wrappers and ECC RTL under
`asic/`, including `asic/common/sram_core.sv` and `asic/rtl/sram/sram_wrappers.sv`.
These are functional digital models, not transistor-level SRAM evidence.

The audit found none of the following:

- a validated 6T SRAM bitcell schematic;
- a bitcell layout or GDS/OASIS view;
- an extracted bitcell or array netlist;
- word-line drivers, precharge, bitline, write-driver, sense-amplifier, column-MUX,
  or decoder circuit netlists;
- characterized bitline/word-line/interconnect parasitics;
- sense-amplifier mismatch or offset models;
- process/mismatch Monte Carlo decks; or
- SRAM macro Liberty/LEF views.

Accordingly, hold/read SNM, write margin, access delay, operation energy, leakage,
retention, disturb, write/access failure, and Qcrit cannot be generated from the local
environment. Existing `data/qcrit_sram6t.json` is already documented by the repository
as unverified example data and is not accepted as physical characterization.

## 6. Existing digital evidence that remains valid

The following capabilities remain useful but do not pass the physical gate:

- deterministic RTL regression through Icarus/Verilator;
- generic Yosys/ABC logical cell and topological-depth reporting;
- existing exact ECC algebra, declared-universe verification, and SafeForge
  certificates; and
- synthetic architecture and transition studies when retained under their existing
  labels.

Prior repository documentation already states that generic Yosys counts are not
physical area, timing, power, or PPA. This audit preserves that conclusion. It does
not relabel prior outputs as physical evidence.

## 7. Required ten-part capability summary

1. **Installed tool versions:** Yosys 0.30+48, Verilator 5.020, and Icarus/VVP 12.0
   development build are verified. Commercial tools, SPICE simulators, OpenRAM,
   OpenSTA, and OpenROAD are not discoverable. Vivado 2019.1 is user-reported only.
2. **Available PDKs:** none usable or verified.
3. **Licensing restrictions:** one generic license environment-variable name exists;
   no value, entitlement, proprietary data, or license terms were captured. No
   proprietary artifact may be committed.
4. **Simulation-model availability:** no transistor, foundry, SRAM, extraction, or
   statistical model deck is available.
5. **Usable process corners:** none.
6. **Usable temperature range:** none for a physical simulation claim. Scenario
   temperatures in legacy inputs are not model-supported corners.
7. **Monte Carlo support:** no process/mismatch Monte Carlo. Existing system-level
   random sampling remains synthetic.
8. **SRAM layout/netlist availability:** behavioral RTL only; no circuit/layout or
   extracted netlist.
9. **Standard-cell library availability:** no characterized library. The Yosys
   functional library is insufficient.
10. **Missing evidence:** transistor/PDK models, lawful PDK access, SRAM circuit and
    extracted views, statistical models, standard-cell Liberty/LEF/GDS, extraction
    rules, SPICE simulation, STA, placement/routing, post-route parasitics, and
    activity-based characterized power.

## 8. Scientific consequence and stop condition

The Stage 1 failure directly triggers the study's publication-failure condition:
the requested physical flow cannot be executed. Continuing would necessarily leave
SRAM failures synthetic and ECC energy as operation-count or generic-cell proxies.
Missing metrics must not be imputed, and `14 nm`, measured silicon, experimental SRAM,
or physical-PPA language remains unsupported.

The following requested deliverables are intentionally **not produced** after this
gate failure: physical preregistration, SRAM method/decks, synthesis/STA/P&R scripts,
activity-power campaigns, physical-characterization records, rerun recommendations,
plots, manuscript claims, or a physical final report.

## 9. Recommended disposition

Package the existing work as a transparently limited thesis validation/negative
methods chapter rather than manufacturing another proxy-based physical study. This
audit can serve as the reproducible reason the physical branch stopped.

A future run may reopen Stage 1 only after one complete, legitimate stack is made
locally accessible and its licenses permit the intended use:

- **Foundry path:** documented ST 65 nm or another foundry PDK, simulator, SRAM
  schematic/extracted views, mismatch models, and matched characterized digital and
  physical libraries; or
- **Open path:** a separately approved SKY130/OpenPDK/OpenRAM/OpenROAD installation,
  with its open-PDK, SRAM, extraction, statistical-model, and power limitations
  explicitly accepted before preregistration.

Installing either stack is a substantial download/configuration action and requires
separate user approval. Merely making Vivado visible would enable a vendor FPGA flow,
but would not supply transistor SRAM characterization or the ASIC PDK/library evidence
required by this study.
