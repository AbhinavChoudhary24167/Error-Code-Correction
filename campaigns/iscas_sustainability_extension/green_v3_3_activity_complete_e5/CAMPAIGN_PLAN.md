# GREEN v3.3 activity-complete E5 campaign plan

## Immutable foundation

This additive campaign starts from matched-campaign seal `8af0fc5a2532b3471016a86cde7968af7d15cfa9` and preserves all GREEN v3.2 files byte-for-byte. The 40 inherited U0, SECDED, Hsiao SECDED, and BCH(78,64,t=2) runs remain the physical population.

## One campaign budget

The hard limit is **15 hours (54,000 seconds for the entire campaign)**. It is not 15 hours per job, phase, architecture, seed, or resume invocation. `RUNTIME_STATE.json` is created once when execution begins and persists one start time and one hard deadline. Every subprocess is limited to `min(explicit_shorter_job_limit, time_remaining_to_campaign_deadline)`; with no shorter limit it receives only the remaining campaign time. New expensive work is not launched within the five-minute deadline guard.

Priority A is the 10 ns U0/SECDED/Hsiao five-seed E5 population. Priority B is timing-labelled 10 ns BCH. Priority C is the 5 ns sensitivity population. A fresh physical rerun is optional because the 40-run v3.2 population is already complete.

## Qualification gates

E5 requires an activity hash, workload hash, exact measurement window and operation count, annotation coverage, final-netlist and SPEF hashes, PVT/clock/seed provenance, and a declared macro-power boundary. Missing data remain null. Vectorless E4 power is never converted to E5 energy.
