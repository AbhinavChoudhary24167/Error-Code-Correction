- Campaign commit: `UNSEALED_WORKTREE`
- Parent GREEN v3.2: `29f20b196e04c713f88fd1a93440a2ff47986f06`

# Architecture audit

This audit is additive to the frozen GREEN Matrix v3.2 campaign. Inclusion is
based on real RTL, a stable mathematical contract, a usable SRAM wrapper, and
fresh regression evidence. `CONDITIONAL_INCLUDE` does not authorize a physical
run in this campaign.

| Architecture | Decision | Width | Fresh validation | Reason |
|---|---:|---:|---|---|
| U0 | INCLUDE | 64 | REGRESSION_VALIDATED | Canonical unprotected payload baseline with a fresh SRAM model round-trip pass. |
| SECDED | INCLUDE | 72 | REGRESSION_VALIDATED | Fresh no-error, all-single, all-double mask-class regressions and SRAM round trip pass. |
| HSIAO_SECDED | INCLUDE | 72 | REGRESSION_VALIDATED | Independent RTL exists and fresh no-error, all-single, all-double class regressions pass. |
| BCH_78_64_T2 | INCLUDE | 78 | REGRESSION_VALIDATED | Fresh no-error and all weight-1/2 mask regressions over four deterministic payloads pass. |
| SEC_DAEC | EXCLUDE | 72 | FAILED | Fresh supported-adjacent-mask regression fails at payload-adjacent bits 4 and 5; physical inclusion is fail-closed. |
| SECDED_PIPELINED | CONDITIONAL_INCLUDE | 72 | NOT_RUN_NO_MEMORY_WRAPPER | Codec is valid, but inventing a memory transaction controller would change the campaign boundary. |
| INTERLEAVED_SECDED_I1_I2 | EXCLUDE | 72 | NOT_RUN_NO_RTL | No real address/data mapping RTL and no exact physical-to-logical topology map exist. |
