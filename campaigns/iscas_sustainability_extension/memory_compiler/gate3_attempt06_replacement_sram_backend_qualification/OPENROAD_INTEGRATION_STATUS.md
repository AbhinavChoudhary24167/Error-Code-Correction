# OpenROAD integration status

Pinned environment: ORFS image `sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e`, SKY130HD TT 25 °C / 1.80 V, OpenROAD `26Q3-1080-gab6fd26351`, KLayout 0.30.7. The SRAMs were imported as unmodified hard macros with published LEF, GDS, and TT Liberty.

## U0 — unprotected 256×64

Synthesis, floorplan, macro placement, PDN, global placement, CTS, and global route completed. The resizer reported `RSZ-0090` because the immutable macro `rstb` input capacitance/transition constraint could not be met by the strongest available SKY130HD driver. The unchanged global-placement database was hash-verified and carried forward only to diagnose later stages; resize is not credited as a pass.

Global route reported one macro, 201,267 µm² macro area, 210,982 µm² total instance area, 9,715.57 µm² standard-cell area, 50.1093% utilization, 205,137 µm wirelength, 458 vias, +2.84127 ns setup slack, +0.00295053 ns hold slack, 139.690 MHz diagnostic fmax, 441 slew and 3 capacitance violations, and 0.985167 mW vectorless power. Detailed route did not converge: the best completed iteration had 144 violations and the last completed iteration had 243. No final GDS is credited. Status: `DETAIL_ROUTE_NOT_CLEAN`.

## E0 — protected 256×64 + 256×8 + Hsiao logic

All stages completed, including detailed route, fill, extraction, reporting, and GDS merge. The final route report has zero routing DRC errors, and the merge found all LEF macros in GDS with no orphan cells. Final metrics: two macros; 260,332 µm² rounded macro area; 278,035 µm² total instance area; 17,703.2 µm² standard-cell area; 37.6773% utilization; 73,538 µm detailed-route wirelength; 7,113 vias; +0.169813 ns setup slack; −0.0067315 ns hold slack with two hold violations; 77 max-slew violations; zero max-cap violations; 101.727 MHz diagnostic fmax; and 1.94783 mW vectorless power. Status: `FINAL_LAYOUT_GENERATED_ROUTE_DRC_CLEAN_TIMING_DRV_VIOLATIONS`.

## Common-stage comparison and qualification boundary

The exact added ECC macro area is 59,064.9696 µm², or 29.3466% of the data-macro area. ECC synthesis logic is 4,710.77 µm². At common global-route stage, E0−U0 setup slack is −2.8715631 ns, fmax is −39.992 MHz, and vectorless power is +1.008633 mW. These are diagnostic displacements only because U0 lacks a clean final route; they are not a matched final-layout experiment or sustainability result.

Overall OpenROAD result is `PARTIAL`: E0 proves hard-macro composition and final layout generation, but U0 fails the mandatory successful baseline routing requirement and both designs expose timing-design-rule limits.

Raw metrics: `raw/openroad/integration_metrics.json`.

