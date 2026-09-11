# Fatal Evidence Gaps

## Central-claim audit

No fatal evidence gap was found for the conditional central claim. The sealed evidence contains ten routed timing-feasible implementations, final-netlist VCD and final SPEF identities, 46 qualified records, full operation counts, and the 23 matched deltas required to test ordering invariance.

## Deliberately out-of-scope gaps

| Gap | Fatal for present claim? | Consequence |
|---|---|---|
| SRAM macro-internal dynamic/standby energy | No | Prohibits whole-memory and silicon energy claims. |
| Delay-annotated glitch activity | No | Qualifies the estimator as final-netlist zero-delay activity. |
| Application traces/weights | No | Prohibits application-average claims. |
| More than five physical seeds | No | Prohibits population-level significance/generalization. |
| Seed-11 idle/write pair | No | Requires n=4 and visible missing cells; prohibits imputation. |
| Other PDKs, corners, voltages, widths, periods | No | Prohibits universal Hamming/Hsiao ranking. |
| Silicon measurement | No | Requires “estimated post-route ECC-logic energy.” |

## Administrative blockers

- `[AUTHOR INPUT REQUIRED]` complete ordered author list for abstract registration.
- `[AUTHOR INPUT REQUIRED]` confirm DATE-specific placement/wording for substantive AI assistance without breaking blind review.
- Portal upload and declarations remain author actions.

These are submission-process blockers, not scientific evidence gaps.

