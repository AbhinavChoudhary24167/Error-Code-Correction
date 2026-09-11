# Gate-3 attempt03 storage and integrity preflight

**Status: PASS.** This preflight was completed before creating or executing any
attempt03 external experiment. Gate 3 remains the finalized `FAIL` recorded in
`../GATE3_STATUS.json`; this diagnostic namespace neither supersedes that result
nor authorizes Gate 4.

## Protected evidence

- All 22 repository files in `../GATE2_GATE3_EVIDENCE_MANIFEST.json` matched
  their recorded SHA-256 digests.
- The attempt01 incident record matched SHA-256
  `76bce8942b510ccfba921b74bd4d470e1f0a24b6b6c093756960f65cb44db72b`.
- All 17 local attempt02 files are covered by the 22-entry manifest and matched.
- All 11 external run04 files in attempt02's generated-artifact manifest matched
  both byte size and SHA-256.
- The complete external attempt02 tree was additionally fingerprinted before
  attempt03: 36,548 files, 5,430,332,296 bytes, tree SHA-256
  `f0dc7607d459831124aed3b767195535d24542ce0a24e62595f8dae7ec20c2b6`.
- The protected DATE verifier reported exactly 7,094 files and empty `changed`,
  `missing`, and `added` lists.

## Storage

At `2026-08-30T17:57:31.6505341+05:30`, Windows reported 19,649,085,440
bytes free on C: and 122,460,368,896 bytes free on F:. WSL `/dev/sdd` was an
ext4 read-write filesystem with 977,756,692,480 bytes available (5% used).
The external campaign root was both readable and writable. Heavy work is
restricted to the new external namespace
`/var/lib/green-ecc-iscas-sustainability/gate3_openram_attempt03_target_diagnosis`.

## Fail-closed decision

All integrity and storage checks passed. Attempt03 may proceed. Any later
integrity mismatch aborts the attempt; no result from attempt03 may edit or
reinterpret the finalized Gate-3 status.
