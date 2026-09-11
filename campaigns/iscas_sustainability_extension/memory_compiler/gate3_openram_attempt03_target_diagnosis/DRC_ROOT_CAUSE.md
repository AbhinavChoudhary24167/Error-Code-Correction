# DRC root-cause classification

## Measurement semantics

The authoritative Magic scalar results are 223,312 error tiles for attempt02 256x72 and 2,140 for the 16x8 control. `drc listall why` occurrences overlap spatially and by rule, so their sums (737,259 and 7,145) are diagnostic histograms, not alternative violation totals. Hierarchical `drc listall count total` likewise double-counts reused cells and must not replace the scalar top-level count.

The diagnostic Tcl was additive instrumentation only (SHA-256 `7db084df0694a47d675e253c3970511af6811cf98b5f168f54f9ebb7d8d137aa`). It loaded the generated GDS with the unmodified pinned Magic deck and queried existing DRC data; it did not waive rules or change geometry.

## Dominant repeated rules

The dominant attempt02 rule-occurrence families are `via.1a+2*via.4a` (114,075), `li.c2` (113,880), `li.3` (95,046), `li.6` (94,900), `via.5a-via.4a` (56,940), `li.c1` (52,489), and `poly.5` (52,341). The corresponding control counts are 1,080, 1,080, 900, 900, 540, 535, and 495. Their attempt02/control ratios cluster around 98-106.

That near-common scaling factor is strong evidence of repeated geometry-rule incompatibilities in the SRAM hierarchy, not 223,312 unrelated hand-layout mistakes. It also appears in `li.1`, `li.5`, `poly.4`, `licon.5a`, and `mcon.1`. Small non-scaling categories such as `met1.2`, `met2.2`, `nwell.7`, and illegal overlap do not dominate the total.

## Hierarchy localization

Magic's per-cell scalar error-tile counts for attempt02 include:

- top macro: 223,312;
- bank: 38,350;
- capped replica array: 38,252;
- replica bitcell array: 38,252;
- main bitcell array: 37,640;
- replica column: 1,708;
- column-cap instances: 1,017 each;
- row-cap instances: 789 each;
- dummy hierarchy: 510;
- primitive cells: repeated fixed counts including 5, 7, 8, 12, 13, and 58.

The control reproduces the same hierarchy pattern at smaller scale: top 2,140; bank 383; capped replica array 380; replica bitcell array 380; main bitcell array 360; replica column 252; column caps 65 each; row caps 117 each; dummy hierarchy 34; and repeated primitive-cell counts.

The errors are therefore distributed through reused bitcell, replica, dummy, cap, local-interconnect/contact, and via geometry. They are not localized to the 72-bit boundary, top-level routing, power ring, or the repair column alone. Because the tiny stock-compatible control fails with the same dominant rule families, target size only replicates an underlying SKY130 primitive-view/verification integration problem.

## Classification

Primary: **F. PDK/VERIFICATION_INTEGRATION_PROBLEM**.

Supporting: **B. SKY130_TECH_PLUGIN_LIMITATION**, insofar as the pinned technology cell/layout views produce systematic violations under their pinned Magic deck.

The evidence does not support a unique 256x72 target-configuration DRC limitation. No DRC deck, rule threshold, or qualification criterion was modified.

