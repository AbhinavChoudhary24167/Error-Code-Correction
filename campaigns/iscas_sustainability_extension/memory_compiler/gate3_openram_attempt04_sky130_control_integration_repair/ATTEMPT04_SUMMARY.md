# Attempt04 summary

Attempt04 reproduced the unchanged stock-compatible 16×8 control at 2,140 DRC errors and LVS FAIL, then performed bottom-up primitive/view bisection. The physical root cause is an incompatible pinned SRAM build-space/view stack: vendor add-mask GDS layers are not materialized by the normal SKY130 Magic import, while the maglef substitutes themselves contain repeated LI/contact/via/well violations. The LVS root cause is connectivity partitioning in imported SRAM views (proxy pins and split WL nets), plus an independent generated well/bulk partition; total device counts match.

The exact upstream SRAM commit labelled “lvs fixes” was tested incrementally in campaign-local OpenRAM copies. Its eight LVS-property edits (P1) and complete ten-file change (P2) left DRC at 2,140 and LVS FAIL with identical device/net counts. No accepted repair was found, so Attempt04 is `CONTROL_INTEGRATION_REPAIR_FAIL` rather than PASS or partial repair.

No 256×8, 256×64, or 256×72 run was executed. No target interface, `spare_wen0`, characterization, Liberty, OpenSTA, OpenROAD, ECC, sustainability, or Gate 4 work was performed. Gate 3 remains finalized `FAIL`; Gate 4 remains `NOT_STARTED_UNAUTHORIZED`.
