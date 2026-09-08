# GREEN v3.3 final report

## Outcome

The campaign infrastructure and evidence audit are complete, but activity-aware power execution is blocked in this environment. This is an honest partial result: **zero E5 records were created**. The one persisted 15-hour campaign budget is implemented and regression-tested; it is never renewed for individual OpenROAD/OpenRAM jobs.

## Required answers

1. Architectures: U0, SECDED, Hsiao SECDED, and BCH(78,64,t=2).
2. Timing-feasible at 10 ns: U0, SECDED, Hsiao SECDED (5/5 setup-feasible seeds each).
3. Timing-feasible at 5 ns: U0 only (5/5 setup-feasible seeds).
4. Fresh RTL-to-GDSII executed: no; it was optional and the complete inherited population was reused.
5. Physical runs completed: 40 inherited, 0 fresh.
6. Fifteen-hour deadline hit: no; expensive execution was not started.
7. Runtime-cutoff runs: none.
8. Post-route activity generated: no.
9. Netlist boundary: not established for activity.
10. Activity format: neither VCD nor SAIF.
11. Explicit annotation fraction: unavailable, not reported as zero.
12. SRAM macro internal power fully characterized: no.
13. Operation classes specified: IDLE/WRITE_CLEAN/READ_CLEAN for U0; those plus single-correct/double-detect for SECDED/Hsiao; those plus one- and two-bit-correct for BCH.
14. Operations planned per class: 256 after 16 warm-up cycles.
15. Quantities promoted to E5: none.
16. E4 diagnostic quantities: inherited area, routing, timing, and vectorless power.
17. Whole-memory E5: not qualified.
18. ECC-logic E5: not yet qualified.
19. Hsiao lower-energy tendency: unresolved.
20. Five-seed operation-energy ordering: unresolved.
21. Hsiao area delta: recorded per seed in `E5_MATCHED_SEED_DELTAS.csv` as inherited physical evidence.
22. Hsiao wirelength delta: recorded per seed in the same table.
23. Hsiao via delta: recorded per seed in the same table.
24. Hsiao timing delta: recorded per seed; Hsiao and SECDED are both feasible at 10 ns.
25. Clean-read energy difference: unavailable.
26. Clean-write energy difference: unavailable.
27. Single-error correction energy difference: unavailable.
28. BCH timing feasible: no, at 10 ns or 5 ns.
29. BCH dominant critical-path stage: not validated by the retained compact reports.
30. BCH in equal-performance E5 Pareto set: no.
31. Globally dominant architecture: none qualified.
32. E5 alteration of E4 ordering: none; there is no E5 evidence.
33. OpenRAM rerun: no; incomplete macro fidelity is documented rather than hidden.
34. Physical/logical topology: not established.
35. Interleaver reliability claim: forbidden.
36. Qcrit claim: forbidden.
37. Physical FIT/SDC/DUE claim: forbidden.
38. Absolute lifecycle-carbon claim: forbidden.
39. Qualified sustainability Pareto front: blocked.
40. Global winner: `NO_GLOBAL_WINNER_QUALIFIED`.
41. Strongest ISCAS-safe claim: a reproducible, timing-partitioned matched physical foundation and deterministic activity-campaign protocol with fail-closed evidence admission.
42. Forbidden: silicon/signoff, E5 energy, complete macro energy, physical reliability, Qcrit, interleaver benefit, absolute SKY130 lifecycle carbon, and a global winner.
43. Highest-value next experiment: execute post-route activity-aware clean read/write and correction power for the 10 ns SECDED/Hsiao matched five-seed set under the shared campaign deadline.
