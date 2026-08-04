# External SRAM and FPGA fault-evidence audit

SafeForge needs bit-exact error vectors in a declared physical word ordering. Most published radiation papers provide aggregate multiplicity, cluster, or cross-section results; those are valuable evidence that SBU-only models are unsafe, but they are not automatically a word-level PMF.

The primary-source audit is machine-readable in `data/fault_evidence/sources.json`. Pérez-Celis and Wirthlin's LANSCE study reports MCU fractions for three SRAM-FPGA families and extracts shapes/frequencies from configuration and block memory. Tsiligiannis et al. classify four MCU types in a commercial 90 nm SRAM exposed to an atmospheric-like neutron beam and report that dynamic operation can produce much larger clusters. These observations justify expanded multi-bit support and geometry-aware sensitivity. They do not supply the physical-logical mapping needed to replay an 8- or 72-bit SRAM word.

No public raw address-level archive with sufficient layout metadata was verified during this phase. Consequently:

- `small_hotspot_8bit.json`, `small_shifted_8bit.json`, and the 72-bit benchmark suite remain explicitly synthetic;
- the literature-derived aggregate envelope is not accepted by the fault-PMF loader and cannot silently become experimental evidence;
- no SafeForge TV or Wasserstein radius is described as statistically calibrated from these papers;
- performance on a literature-derived bit-exact PMF is **not available** and is reported as a limitation, not fabricated by spreading aggregate MCU mass across arbitrary positions.

Future ingestion requires the original upset-address list, irradiation conditions and fluence, device/array geometry, logical-to-physical address mapping, word/interleave mapping, readout interval, event-clustering rule, and units. A digitized plot must additionally store the source figure, calibration points, extraction tool/version, and uncertainty.
