# Final scientific report

Classification: `GREEN_V3_2_MATCHED_ORFS_MULTI_ARCH_PHYSICAL_VALIDATION_COMPLETE_OPENRAM_REGENERATION_PARTIAL_RUNTIME_CUTOFF_INHERITED_SRAM_MACROS_E4_E5_PENDING_ABSOLUTE_RELIABILITY_AND_LIFECYCLE_BLOCKED`

This campaign is additive to frozen GREEN Matrix v3.2. Physical implementation
measurements are treated as tool-derived evidence and are not conflated with
silicon or radiation measurements. GREEN v3.2 propagates only evidence
compatible with the required technology, workload, measurement boundary, and
semantic qualification.

The initial ten Hsiao runs are preserved as failed experiments. Their common
ORFS inference-threshold integration defect was repaired by allowing the
unchanged combinational syndrome table to reach `memory_map`; this recorded
architecture-specific exception does not modify ECC semantics.

## Answers to the required scientific questions

1. Audited U0, conventional and pipelined SECDED, Hsiao SECDED, bounded SEC-DAEC, BCH(78,64,t=2), and I1/I2 interleaver proposals.
2. Included U0, SECDED, HSIAO_SECDED, BCH_78_64_T2.
3. SEC-DAEC failed a fresh adjacent-pair check; pipelined SECDED lacks a validated SRAM controller wrapper; I1/I2 have no RTL/topology map.
4. Fresh OpenRAM status: TIMEOUT.
5. Fresh OpenRAM artifacts: openram_log.
6. No. The failed fresh 256x72 target is not substituted; ORFS uses separately inherited SRAM22 macros.
7. U0 uses 64 physical bits, SECDED variants use 72, and BCH uses 80 physical macro bits for 78 code bits.
8. 16,384 user payload bits (256 × 64) per architecture.
9. U0: 0; SECDED/Hsiao: 2,048; BCH: 4,096 physical bits including 512 padding bits.
10. No. 4 of 5 freshly executed candidates passed; SEC-DAEC failed.
11. Frozen exact evidence exists for conventional SECDED, Hsiao, and BCH; fresh runs are finite-payload exhaustive-mask regressions, not unrestricted proofs.
12. Synthesis artifacts: 40 of 40 planned runs.
13. Placement artifacts: 40 runs.
14. Routes: 40 runs.
15. GDS: 40 runs.
16. External detailed routing is classified per run; macro-internal DRC is not independently signoff-qualified.
17. LVS is unavailable/not independently reproduced for the matched top levels.
18. Fresh OpenRAM DRC classification: DRC_NOT_COMPLETED_BEFORE_RUNTIME_CUTOFF; no array violation is silently waived.
19. Five seeds completed per architecture/condition: True.
20. Two timing conditions completed: True.
21. Area mean/dispersion values are in SEED_STATISTICS.json/csv.
22. Wirelength mean/dispersion values are in SEED_STATISTICS.json/csv.
23. Via mean/dispersion values are in SEED_STATISTICS.json/csv.
24. Timing mean/dispersion values are in SEED_STATISTICS.json/csv.
25. Vectorless power mean/dispersion values are in SEED_STATISTICS.json/csv and remain E4 diagnostic.
26. Most compact by mean 10 ns total instance area: U0.
27. Lowest mean 10 ns diagnostic total power: U0.
28. Best mean 10 ns setup slack: U0.
29. Ordering stability is reported as matched-seed fractions in SEED_STATISTICS.json; n=5 is not overinterpreted.
30. Architecture breadth beyond U0/E0: yes.
31. Diagnostic implementation Pareto: AVAILABLE_MULTI_ARCH_POPULATION_SINGLETON_U0_E4_DIAGNOSTIC_FRONT; the physical-only front is not called nontrivial when U0 dominates every measured implementation objective.
32. E5 energy did not become qualified.
33. Missing isolated operation windows, complete activity annotation, counted operations, and macro-internal activity characterization block E5.
34. I1/I2 were not physically implemented.
35. I1/I2 overhead is unknown, not zero.
36. Complete physical/logical bit mapping was not established.
37. Interleaver reliability benefit cannot be claimed.
38. Physical SDC/DUE/FIT cannot be claimed.
39. Qcrit cannot be claimed.
40. SKY130 manufacturing/lifecycle carbon cannot be claimed.
41. A qualified sustainability front does not exist.
42. A global winner cannot be claimed: NO_GLOBAL_WINNER_QUALIFIED.
43. ISCAS-safe claims: fresh functional regression where passed, matched ORFS RTL-to-GDS implementation where completed, multi-seed E4 characterization, and exact inherited conditional logical evidence where cited.
44. Forbidden: tapeout, foundry signoff, silicon/radiation validation, physical event rates/FIT/SDC/DUE, Qcrit, E5 energy, absolute lifecycle carbon, or a global winner.
45. Highest-value next experiment: activity-complete post-route operation-class power on the matched population.

## Multi-seed descriptive results

Values are mean ± sample standard deviation over five seeds.

| Architecture | Clock ns | Total instance area µm² | Wirelength µm | Vias | Setup WNS ns | Vectorless power W |
|---|---:|---:|---:|---:|---:|---:|
| U0 | 10 | 206791 ± 0 | 21082.4 ± 7.47 | 1223.2 ± 45.8 | 3.96271 ± 0.00445 | 0.000801186 ± 1.6e-07 |
| SECDED | 10 | 273980 ± 46 | 73141.2 ± 1.12e+03 | 5595.2 ± 18.7 | 0.433752 ± 0.18 | 0.00228818 ± 2.05e-05 |
| HSIAO_SECDED | 10 | 274217 ± 36 | 76134 ± 164 | 6063 ± 45.8 | 0.677443 ± 0.146 | 0.00197349 ± 6.93e-06 |
| BCH_78_64_T2 | 10 | 379596 ± 1.27e+03 | 296299 ± 1.64e+03 | 36519.6 ± 277 | -11.112 ± 0.143 | 0.0612421 ± 0.00224 |
| U0 | 5 | 206693 ± 0 | 21055.2 ± 7.66 | 1191.2 ± 45.8 | 0.288042 ± 0.00431 | 0.00159469 ± 3.1e-07 |
| SECDED | 5 | 277136 ± 184 | 75788.8 ± 316 | 6149.6 ± 24.2 | -3.18143 ± 0.0783 | 0.00450958 ± 2.46e-05 |
| HSIAO_SECDED | 5 | 277699 ± 244 | 78549.4 ± 718 | 6370 ± 9.92 | -2.83509 ± 0.0227 | 0.00395011 ± 9.05e-06 |
| BCH_78_64_T2 | 5 | 380694 ± 624 | 295151 ± 2.96e+03 | 36768.2 ± 165 | -15.7141 ± 0.136 | 0.112983 ± 0.0103 |
