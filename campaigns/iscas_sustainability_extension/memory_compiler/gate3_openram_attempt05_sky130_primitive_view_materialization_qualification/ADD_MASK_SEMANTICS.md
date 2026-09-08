# SKY130 SRAM add-mask semantics

## Decision

The four records are identifiable, but the boolean/electrical materialization semantics required for `CLI1MADD`, Magic's `CNTMADD` alias, and `CP1MADD` are **not established**. Their mapping confidence is `UNKNOWN`; no materialization transform is authorized.

NCM is separately and authoritatively identified as N-core implant geometry. It participates in device classification and is not an add-mask alias to ordinary interconnect or poly.

| Observed name | GDS | Authoritative pinned-PDK identification | Category | Ordinary layer modified | Boolean/order | Mapping confidence |
|---|---:|---|---|---|---|---|
| `CLI1MADD` | 115/43 | `cli1m, mask add` | manufacturing mask-add augmentation | unknown | unknown | `UNKNOWN` |
| `CNTMADD` | 22/21 | `cfom, mask add`; Magic's symbolic name conflicts | manufacturing mask-add augmentation | unknown | unknown | `UNKNOWN` |
| `CP1MADD` | 33/43 | `cp1m, mask add` | manufacturing mask-add augmentation | unknown | unknown | `UNKNOWN` |
| `NCM` | 92/44 | `ncm, drawing, N-core implant` | standalone implant / verification device classification | none | no materialization; used during gate derivation | `AUTHORITATIVELY_CONFIRMED` |

## Evidence and limits

The pinned SkyWater `gds_layers.csv` is decisive for names, datatypes, and the generic `mask add` purpose. It also exposes the 22/21 conflict: `cntm, mask add` is actually 26/21, while 22/21 is `cfom, mask add`. The installed `sky130A-GDS.tech` calls 22/21 `CNTMADD`, but only preserves it on an isolated identifier-like plane. It gives no boolean composition. The normal `sky130A.tech` does not map any of 115/43, 22/21, 33/43, or 92/44, matching the fresh GDS-import warnings.

The upstream open_pdks GDS-only technology explicitly says it represents vendor layers without boolean transforms and does not properly understand connectivity, so its block/identifier-plane placement cannot be repurposed as an electrical mapping. See [upstream `sky130gds.tech`](https://github.com/fossi-foundation/open-pdks/blob/main/sky130/magic/sky130gds.tech) and the [historical tagged source](https://foss-eda-tools.googlesource.com/third_party/opencircuitdesign.com/open_pdks/%2B/refs/tags/1.0.210/sky130/magic/sky130gds.tech?autodive=0%2F%2F%2F%2F%2F%2F%2F).

For NCM, the pinned SkyWater masks and layer-description tables call 92/44 `N-Core Implant`; minimum-width/spacing and core/periphery rules further show that it is real standalone mask geometry. The pinned `sky130.lylvs` reads it directly and subtracts it while deriving standard/HVT/HV transistor-gate regions. This confirms a device-classification role, not `OR` composition into LI, contact, or poly.

The pinned SRAM repository README describes a build space but supplies no add-mask materialization script or process equation. Focused searches of the pinned PDK, SRAM repository, OpenRAM technology collateral, and locally available history found no such procedure. That absence is recorded as “not found,” not proof that proprietary manufacturing semantics do not exist.

## Preserved local evidence

- `raw/semantics/skywater_gds_layers.csv` (`a424c152e2d300992f743f17abdb6fb72402c4c9a4bbdcdbab439757fd0c89b5`)
- `raw/semantics/skywater_masks.csv` (`85948e753aeb125337f3238e9479a58eafeb4c0050bdc888930f1401ec513ae1`)
- `raw/semantics/skywater_table-c4b-layer-description.csv` (`dcfeb27a76171a67ca6a905bdc6deab0ca4d801f5970a76b1ce90aebb97bb21f`)
- `raw/semantics/skywater_table-f2b-mask.tsv` (`7db89f09785ab8508ec0cef35cb0ce2a97a18241a3e54294a49c489c2cbaf47a`)
- `raw/semantics/skywater_assumptions_02-mins.csv` and `skywater_assumptions_07-other.csv`
- `raw/semantics/openram_sky130.lylvs` (`cb5d388070b3fa325002f341d89436763b3199ac5fbc9a12ff90a810ea5d7eda`)
- `raw/semantics/sky130_fd_bd_sram_README.rst`
- `raw/tool_configuration/sky130A-GDS.tech`, `sky130A.tech`, `sky130A_setup.tcl`, OpenRAM `.magicrc`, and `tech.py`

No layer name alone was treated as proof. In particular, this campaign does **not** infer `CLI1MADD -> LI1`, `CNTMADD -> contact`, or `CP1MADD -> poly`.
