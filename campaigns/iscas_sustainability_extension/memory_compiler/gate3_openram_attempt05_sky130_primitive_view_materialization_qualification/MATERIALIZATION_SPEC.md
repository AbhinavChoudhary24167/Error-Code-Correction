# Materialization specification

## Executed transform

None.

The required semantics for the three mask-add records are `UNKNOWN`, and the 22/21 record has a direct naming conflict between the pinned SkyWater layer table (`cfom, mask add`) and the installed Magic GDS-only alias (`CNTMADD`). Under the campaign rule, neither `AMBIGUOUS` nor `UNKNOWN` mappings may be used for qualification.

Consequently there is no `materialize_sky130_sram_views.py`, no output GDS, no polygon edit, and no boolean equation applied. Candidate equations such as `LI_final = LI_base OR CLI1MADD`, `contact_final = contact_base OR CNTMADD`, or `poly_final = poly_base OR CP1MADD` were explicitly rejected as unsupported.

The only “post” identity entries in the leaf matrix are unchanged source views that already have zero DRC and LVS PASS. They are not materialized outputs.
