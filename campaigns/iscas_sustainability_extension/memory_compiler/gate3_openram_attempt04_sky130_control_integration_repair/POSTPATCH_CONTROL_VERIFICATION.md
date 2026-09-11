# Post-patch control verification

The final P2 run used the exact same 1,146-byte configuration and the same OpenRAM, PDK, container, Magic, Netgen, corner, voltage, and temperature. Only the ten files from exact upstream SRAM commit `8dccd8d...` existed in the campaign-local source copy.

The result is unchanged: OpenRAM exit 1, DRC 2,140, LVS FAIL, 1,802/1,802 devices, and 658/698 extracted/schematic nets. The P1 and P2 LVS reports are byte-identical (`d4b794d0a6e4848c192e336ceb43eff11cb89d22f5ce0f7726e6263fa27284b9`), demonstrating that the remaining two files in P2 did not affect the connectivity comparison. The known `nom_corner` exception appeared only after DRC/LVS and remains out of scope.

No waiver, verifier disabling, deck edit, black-box masking, target simplification, or unrelated memory substitution was used. Because neither DRC nor LVS materially improved, the correct classification is `CONTROL_INTEGRATION_REPAIR_FAIL`.
