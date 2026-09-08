# Functional validation summary

- Campaign commit: `UNSEALED_WORKTREE`
- Parent GREEN v3.2: `29f20b196e04c713f88fd1a93440a2ff47986f06`

| Architecture | Status | Scope |
|---|---|---|
| U0 | REGRESSION_VALIDATED | Four deterministic no-error SRAM-model round trips; no protection capability is claimed for U0. |
| SECDED | REGRESSION_VALIDATED | All weight-1 correction and weight-2 detection masks are enumerated over four deterministic payloads; frozen exact evidence supplies the unrestricted linear-code result. |
| HSIAO_SECDED | REGRESSION_VALIDATED | All weight-1 correction and weight-2 detection masks are enumerated over four deterministic payloads; this fresh run is not relabelled as an unrestricted proof. |
| BCH_78_64_T2 | REGRESSION_VALIDATED | All declared weight-1/2 correction masks are enumerated over four payloads; weight-3 behavior is outside the correction guarantee and remains inherited observation-only evidence. |
| SEC_DAEC | FAILED | The declared data-adjacent pair class is tested over four payloads and contains a preserved counterexample; the candidate is excluded. |
