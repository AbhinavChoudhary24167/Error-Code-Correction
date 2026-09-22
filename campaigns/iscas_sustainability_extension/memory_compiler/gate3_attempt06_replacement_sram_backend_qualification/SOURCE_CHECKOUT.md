# SRAM22 source checkout

The SRAM22 macro repository is an external dependency and is not vendored in this repository. Attempt 06 used:

- repository: `https://github.com/ucb-substrate/sram22_sky130_macros.git`
- commit: `75cbe961e18ee00d5a6c73fa455505f0bcdf4c05`

From this directory, materialize the expected local path with:

```bash
git clone --filter=blob:none https://github.com/ucb-substrate/sram22_sky130_macros.git source_checkout
git -C source_checkout checkout 75cbe961e18ee00d5a6c73fa455505f0bcdf4c05
```

The `source_checkout/` directory is ignored by the parent repository. Its license and upstream history remain authoritative. `SRAM22_SOURCE_MANIFEST.json`, `ATTEMPT06_STATUS.json`, and the campaign evidence manifest record the source identity and the views used by the historical run.
