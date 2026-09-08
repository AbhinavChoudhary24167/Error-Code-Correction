# Control integration after leaf qualification

The unchanged 16x8 control was **not run**. `LEAF_QUALIFICATION_GATE.json` is `FAIL`, so section 15 of the campaign contract prohibited a speculative macro execution.

The copied configuration at `raw/control_integration/control_8x16_config.py` is byte-identical to Attempt04 with SHA-256 `dc22607f0f35e401fade14046b8089cfb3f04f9db1db84bb6e24c09f9fb82fd6`. No dimension, architecture, muxing, port, or interface change was made.

Attempt04's established 2,140 DRC tiles, LVS FAIL, 1,802/1,802 devices, and 658/698 nets remain historical context only; they are not reported as fresh Attempt05 results.
