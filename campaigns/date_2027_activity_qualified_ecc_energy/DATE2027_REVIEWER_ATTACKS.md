# Reviewer Attacks and Prepared Responses

## D9 reviewer

**Attack:** The conclusion “activity matters” is elementary.  
**Response:** The paper quantifies an ordering failure under a controlled substitution: 5/5 vectorless Hsiao-lower becomes 4/23 operation-specific Hsiao-lower on the same ten qualified routes.

**Attack:** Energy values exclude the dominant SRAM macro.  
**Response:** Correct; every headline statement says ECC-logic energy. The paper contributes a boundary-qualified architecture result and identifies macro characterization as the necessary next experiment for whole-memory claims.

**Attack:** Synthetic operations are not applications.  
**Response:** They are controlled basis operations. The workload-mixture equation exposes rather than hides application weights; no application-average claim is made.

**Attack:** Zero-delay activity misses hazards.  
**Response:** Named in threats. The experiment compares an explicit final-netlist activity estimator against a vectorless diagnostic, not silicon current.

## D13 reviewer

**Attack:** Physical design is merely a tool invocation.  
**Response:** Final-route identity, final SPEF, timing admission, and seed pairing are necessary controls. Removing them makes estimator substitution uninterpretable.

**Attack:** Small seed count permits implementation noise.  
**Response:** Every pair is shown. Seed dispersion is itself a result; no broad significance inference is attempted.

**Attack:** Timing headroom differs.  
**Response:** All runs satisfy the fixed 10-ns target; WNS is reported independently and is not converted into energy.

## Methodology reviewer

**Attack:** Missing seed-11 idle/write records could bias totals.  
**Response:** There is no pooled grand mean in the claim, missing cells are visible, and operation denominators are 4 or 5 as appropriate.

**Attack:** Hashes do not prove correctness.  
**Response:** Agreed. Hashes prove identity; interface tests, activity coverage, and physical qualification address other failure modes. The distinction is explicit.

**Attack:** Component decomposition is a post-hoc story.  
**Response:** It is labeled diagnostic. The central result is the directly observed paired total-energy sign.

## Fatal attack threshold

Any discovered netlist/SPEF/VCD identity mismatch, timing-infeasible admitted run, incorrect operation denominator, macro-inclusive wording, or unverified central citation blocks submission until corrected.

