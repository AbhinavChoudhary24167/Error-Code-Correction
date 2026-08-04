# External SRAM and FPGA fault-evidence audit

SafeForge consumes bit-exact error vectors in a declared physical word ordering. Published radiation and undervolting studies usually provide multiplicity or spatial aggregates instead. This phase uses those aggregates directly as uncertainty constraints and never labels a synthetic allocation as a measured PMF.

The machine-readable provenance is `data/fault_evidence/sources.json`. It records source, device/technology, experiment, extracted statistic, extraction method, uncertainty status, and mapping assumptions.

## Source-specific evidence retained

- **Pieper et al. (2023), 5-nm bulk-FinFET SRAM:** alpha, neutron, heavy-ion, and voltage campaigns. The alpha result that multicell upsets exceed 15% below 550 mV becomes `P(multiplicity>=2) in [0.15,1]`. The reported three-cell clustering rule is retained, but cannot be mapped to logical-word adjacency without layout/interleaving metadata.
- **Perez-Celis and Wirthlin (2020), SRAM FPGA under LANSCE neutrons:** classified MCU fractions `0.277`, `0.1459`, and `0.0559` across device families define a sensitivity interval `[0.0559,0.277]`, not a pooled sampling confidence interval.
- **Salami et al. (2019), undervolted FPGA BRAM:** the greater-than-90% correctable aggregate, attributed by the authors to single-bit faults, gives `P(multiplicity=1) in [0.90,1]`. The additional rounded detectable fraction is not converted to a DBU PMF.
- **Soyturk et al. (2019), undervolted SRAM maps:** 14,420 maps, 2,174 faulty maps, and reported faulty-bit-count/spatial-column aggregates support structured sensitivity. Persistent fault count per SRAM macro is not transient event multiplicity within one ECC word.
- **NASA Kintex UltraScale heavy-ion report:** the public methodology supports multiplicity collection, but no reusable numeric histogram was recovered; no numeric constraint is instantiated.

## Executable ambiguity sets

Three separate configurations are evaluated:

- `configs/ambiguity/literature_pieper_5nm_alpha_72bit.json`
- `configs/ambiguity/literature_fpga_neutron_mcu_72bit.json`
- `configs/ambiguity/literature_fpga_bram_undervolt_72bit.json`

Each structured set contains every PMF on the executable synthetic bit support consistent with the stated category aggregate. The nominal synthetic PMF only provides the bit-level support and center; the source aggregate supplies the literature constraint. Literature-derived and synthetic result labels remain distinct. All nine emitted SDC/DUE/residual certificates pass the independent solver-free verifier.

## What is not available

No public raw address-level archive with a verified physical/logical map was ingested. Consequently no SafeForge result is described as measured silicon behavior, no aggregate interval is called a statistical confidence interval unless the source provides one, and no literature set removes the explicit probability tail outside the executable weight-one-through-three support.

Future bit-exact ingestion requires upset addresses, irradiation/voltage conditions, fluence or exposure, device geometry, logical-to-physical and interleave mappings, readout interval, clustering rule, and units. Plot digitization would additionally require the source figure, calibration points, tool/version, and extraction uncertainty.
