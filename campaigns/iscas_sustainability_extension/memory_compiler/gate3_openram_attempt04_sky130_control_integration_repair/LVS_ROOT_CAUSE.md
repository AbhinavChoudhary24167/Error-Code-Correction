# LVS root cause

DRC and LVS do not reduce to a single parameter typo. The LVS failure is a connectivity and primitive-view consistency failure produced by the same incomplete physical-view integration, with an additional generated well/bulk partition symptom.

At the top, device totals are identical (1,802 extracted and 1,802 schematic), but connectivity is not (658 extracted versus 698 schematic nets). The bank is likewise device-identical at 1,786/1,786 and net-mismatched at 643/665. This excludes missing-device generation as the primary mechanism.

The earliest imported-view evidence is at the leaf SRAM hierarchy:

- `sram_sp_colend` and `sram_sp_colenda` each compare as a one-device leaf, yet extraction exposes `m2_0_4#` and `m2_0_236#` proxy pins and reports `bl`, `vdd`, `gnd`, and `vpb` disconnected across split copies. Those partitions are then repeated in the capped/replica hierarchy.
- Replica bitcells have 8/8 devices but 9 extracted versus 8 schematic nets; the extracted `WL` connectivity is split across `WL` and an unnamed node.
- Main bitcells have 8/8 devices but 10 extracted versus 9 schematic nets and the same missing/split `WL` connectivity.
- Independently, generated `pnand2_0` has 4/4 devices and 7 extracted versus 6 schematic nets; a PFET bulk/well node is separate from `vdd`. Generated `pnand3` has the corresponding 6/6-device, 9/8-net split.

Pin names and power-name case are normalized successfully by Netgen in many matching leaves, and device classes are equated. The failure is therefore not a simple subcircuit-name or pin-order error. It is not the 256×72 scalar/indexed `spare_wen0` defect; that target was never run here.

P1 applied the eight LVS-view parameter changes from upstream SRAM commit `8dccd8d...`. P2 completed that exact commit with its dummy maglef and ordinary SPICE changes. Neither changed any device/net count, mismatch class, or final result. P1 and P2 Netgen reports are byte-identical. The upstream normalization merely causes Netgen to list `colend` and `colenda` property errors explicitly; it does not reconnect the proxy/WL/well partitions. This causal negative result rules out parameter normalization as a sufficient repair.
