# Attempt05 summary

Attempt05 is classified **`MATERIALIZATION_SEMANTICS_UNRESOLVED`** with recommendation **`STOP_OPENRAM_SKY130_BACKEND`**.

The pinned PDK authoritatively identifies 115/43 and 33/43 as mask-add records and 92/44 as N-core implant, but supplies no boolean/electrical composition equation for the mask-add records. More seriously, the installed Magic GDS-only technology calls 22/21 `CNTMADD`, while the pinned SkyWater table calls it `cfom, mask add` and assigns actual `cntm, mask add` to 26/21. Public open_pdks documents its vendor-GDS technology as a layer-preserving, non-extraction view. A truthful electrical rewrite therefore cannot be chosen.

No geometry transformation was performed. Direct original-GDS baselines under the normal pinned flow show `colend` at 39 DRC tiles and LVS FAIL because `gate` is missing from the extracted boundary; `colenda` has standalone LVS equivalence but 38 DRC tiles; ordinary bitcells have 126 DRC tiles and LVS FAIL at 8/8 devices, 10/9 nets; replicas and the dummy retain the corresponding split/unmatched wordline partitions. Only two of 29 required source views qualify unchanged, so the leaf gate failed and correctly prohibited an unchanged-control rerun.

The generated `pnand2_0` defect was freshly reproduced independently: 0 DRC, 4/4 devices, 8/6 nets, LVS FAIL from isolated well/substrate partitions. Its flat generated MAG contains no imported SRAM hard-cell instance.

All 7,094 protected DATE files and prior repository manifests rehash cleanly. The original Attempt02/03 external WSL trees remain `NOT_REVERIFIED` due the documented VHDX sharing violation. `make` passed; `make test` and full pytest reproduced exactly the two frozen validator failures with no new regressions; six campaign-local tests passed. The relinked protected binary was restored to SHA-256 `99fbb17b7a9bc4296d6a044e5edc496f131def71e532062b563a776ab31e06ef`.

Gate 3 remains `FAIL`; Gate 4 remains `NOT_STARTED_UNAUTHORIZED`. No Attempt06 was started.
