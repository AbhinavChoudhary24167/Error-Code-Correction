# DRC root cause

## Finding

The pinned OpenRAM 1.2.48 SKY130 plugin and pinned `sky130_fd_bd_sram` commit `dd642569...` do not form a signoff-clean physical-view stack under the pinned normal `sky130A` Magic technology. The SRAM library GDS contains build-space/add-mask layers that the normal import style does not materialize: layer/datatype 115/43 (`CLI1MADD`), 22/21 (`CNTMADD`), 33/43 (`CP1MADD`), and 92/44 (`NCM`). Magic logs them as unknown during direct GDS import. Losing those masks changes local-interconnect/contact/poly/well materialization.

OpenRAM avoids most of that damage by substituting vendor maglef abstracts for SRAM leaves during its ordinary verification flow. Those abstracts are not clean physical signoff views: isolated leaf checks reproduce 5–13 error tiles in bitcells, colends, corners, row ends, and wordline straps. The array hierarchy then replicates them into 360–380-tile array failures and a 2,140-tile top failure.

This conclusion is falsifiable and is supported by three measurements:

1. Ordinary OpenRAM verification with maglef substitution reports 2,140 top error tiles and 7,145 rule occurrences.
2. Leaf maglef views independently reproduce the same LI/contact/via rule families.
3. Direct import of the generated GDS through the normal `sky130A` technology (no maglef overwrite) logs the unknown add-mask layers and becomes much worse: 24,395 top error tiles and 103,615 rule occurrences, including 19,762 in the main bitcell array and 24,324 in each replica/capped array.

## Dominant rule families

The ordinary-flow histogram is: via1 width 1,080; core-LI spacing 1,080; LI spacing 900; LI minimum area 900; metal1/via1 enclosure 540; core-LI width 535; poly/tap spacing 495; licon width 352; LI/contact enclosure 291; LI width 289; licon/diffusion enclosure 281; mcon width 225; poly/diffusion spacing 90; diffusion width 47; illegal overlap 27; metal1 spacing 8; nwell spacing 5 total.

These are rule occurrences, not unique geometry count. Error-tile hierarchy attribution is non-additive because parent/child boxes overlap. It nevertheless demonstrates replication: leaf bitcells are 8 tiles, `colend`/`colenda` 7, corners 5, straps 12–13; generated main/replica/capped arrays are 360/380/380; the bank is 383; the top is 2,140.

## Rejected false repairs

- `drc(full)` is not a repair: it reports 2,144 tiles and adds well/tap checks.
- Direct normal-tech GDS import is not a repair: it drops add-mask data and reports 24,395 tiles.
- `sky130A-GDS.tech` is a vendor/supplementary mapping and DRC aid, not the full pinned signoff deck. Selecting it alone would disable most checks and violate the no-disabling/no-masking rule.
- Black-boxing SRAM leaves, waiving rules, changing the DRC deck, or replacing the memory was not used.

The minimum credible future repair is a separately qualified SRAM view-materialization/technology integration that composes the vendor add masks into normal SKY130 electrical layers and then proves the resulting hard-cell layouts against the full unmodified signoff checks. That is larger than the audited patch family authorized here.
