# GREEN v3.3 final report

## Outcome

The campaign achieved **LEVEL B — strong**: 46 post-route, activity-aware, parasitic-aware ECC-logic E5 measurements across five matched SECDED/Hsiao seeds. All five seed pairs qualify for three read classes; four qualify for the complete five-class set. The single 54,000-second campaign budget was never reset per run.

Hsiao did **not** retain a generally lower operation-energy tendency: it was lower in only 4/23 matched comparisons (17.39%). Whole-memory energy remains unqualified because SRAM macro-internal characterization is incomplete.

## Required answers

1. Architectures included in the source population: U0, SECDED, Hsiao SECDED, and BCH(78,64,t=2); v3.3 E5 execution covered SECDED and Hsiao.
2. Timing-feasible at 10 ns: U0, SECDED, and Hsiao SECDED in the inherited five-seed partition; all ten fresh SECDED/Hsiao runs were feasible.
3. Timing-feasible at 5 ns: U0 only in inherited evidence.
4. Fresh RTL-to-GDSII campaign executed: yes, for SECDED/Hsiao at five 10 ns seeds each.
5. Physical runs completed: 50 represented in the combined evidence base.
6. Inherited versus fresh: 40 inherited and 10 fresh.
7. Campaign budget consumed: 23874.583 seconds (6.632 hours, 44.21% of 54,000 seconds).
8. Global deadline reached: no; queued execution ended before `2026-09-09T12:30:53.296930Z`.
9. Runtime-cutoff experiments: none. Lower-priority work was not launched after the deadline.
10. Post-route activity generated: yes.
11. Boundary: zero-delay final-routed gate-netlist VCD, with final SPEF used in OpenROAD/OpenSTA power.
12. Activity format: VCD only.
13. Annotation coverage: functional logic 99.298%–99.356%; all 72 required macro-output roots per qualified record.
14. SRAM macro internal power fully characterized: no.
15. Characterized classes: IDLE, WRITE_CLEAN, READ_CLEAN, READ_SINGLE_BIT_ERROR_CORRECT, and READ_DOUBLE_BIT_ERROR_DETECT for SECDED/Hsiao; seed 11 qualifies only the three read classes.
16. Operations measured: exactly 256 per class after 16 warm-up cycles.
17. E5 quantities: ECC-logic internal/switching/leakage/total power and operation-normalized energy for 46 records.
18. E4 diagnostic quantities: inherited area, routing, timing, and vectorless power; incomplete macro power is not promoted.
19. Whole-memory E5 qualified: no.
20. ECC-logic-only E5 qualified: yes.
21. Matched SECDED/Hsiao seeds completed: five for reads; four for all five classes.
22. Hsiao retained lower energy: no, not generally.
23. Ordering held for every seed: no.
24. Ordering held across operation classes: no; Hsiao was lower in 4/23 matched cells.
25. Hsiao total-instance-area difference: mean +237.6000 um^2 across the inherited matched seeds.
26. Hsiao wirelength difference: mean +2992.8000 um.
27. Hsiao via difference: mean +467.8000 vias.
28. Hsiao setup-WNS difference: mean 0.2437 ns; better in four of five inherited matched seeds.
29. Clean-read energy difference (Hsiao minus SECDED): mean -0.0308 pJ/op over five seeds; Hsiao lower in 3/5.
30. Clean-write energy difference: mean 0.1207 pJ/op over four qualified seeds; Hsiao lower in 0/4.
31. Single-error-correction energy difference: mean 0.3095 pJ/op over five seeds; Hsiao lower in 0/5.
32. Double-error-detection energy difference: mean 0.1935 pJ/op over five seeds; Hsiao lower in 0/5.
33. E5 versus E4 ordering: E5 mostly reverses the vectorless E4 Hsiao-lower tendency (4/23 E5 cells retain it versus 5/5 E4 seed-level power comparisons).
34. BCH timing feasible: no, at 10 ns or 5 ns in inherited evidence.
35. BCH critical-path dominant stage: not validated by retained stage-attributed timing evidence.
36. BCH activity characterized: no.
37. BCH eligible for the equal-performance E5 front: no.
38. U0 E5 baseline: no.
39. 5 ns E5 evidence: none.
40. OpenRAM rerun: no; it was not allowed to displace the primary matched experiment.
41. Physical/logical bit topology established: no.
42. Interleaver reliability claim: no.
43. Qcrit claim: no.
44. Physical FIT/SDC/DUE claim: no.
45. Absolute lifecycle-carbon claim: no.
46. Qualified sustainability Pareto front: no.
47. Global winner: `NO_GLOBAL_WINNER_QUALIFIED`.
48. Source/evidence files deleted during active execution: none.
49. Testing mutations: an early focused test regenerated placeholder reports/queue and exposed the stale hash; Windows Git also reported future LF-to-CRLF checkout warnings. Final validation mutations are recorded separately.
50. Cleanup postponed: all cache, fixture, duplicate, and uncertain cleanup.
51. Files eventually cleaned: none.
52. Frozen v3.2 integrity preserved: yes, guarded against its pinned seal commit.
53. Strongest ISCAS-safe claim: matched post-route activity and parasitic-aware ECC-logic energy shows the vectorless Hsiao-lower tendency is not robust across operation classes in this descriptive sample.
54. Still forbidden: silicon/foundry signoff, unrestricted whole-memory energy, physical SER/FIT/SDC/DUE/Qcrit, interleaver benefit, absolute SKY130 lifecycle carbon, imec certification/endorsement, and a global winner.
55. Highest-value next experiment: under a newly authorized campaign budget, add the matched five-seed 10 ns U0 IDLE/WRITE_CLEAN/READ_CLEAN baseline using the now-qualified pipeline.
