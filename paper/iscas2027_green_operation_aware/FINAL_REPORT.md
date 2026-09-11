# Final report

Evidence seal: `8cf245ac6ac8cb9b010c073d439f04eb204d48a1`. Analysis scope: additive files under `paper/iscas2027_green_operation_aware/`; no frozen campaign file is modified.

1. **What exact research question does the manuscript answer?** Whether an ECC architecture preference inferred from reliability and conventional vectorless physical-design power remains valid when matched post-route implementations are evaluated using operation-specific switching activity.

2. **What is GREEN's role in answering it?** GREEN is the evidence-qualified decision method: it qualifies provenance and abstraction, applies hard reliability/timing constraints, retains missing values, then constructs operation-aware, Pareto, and workload-dependent comparisons. It is not the experiment or a mandatory weighted score.

3. **What is the strongest qualified result?** Under the evaluated 10 ns matched implementations, the Hsiao-lower E4 vectorless tendency is not generally preserved under E5 operation-specific activity: Hsiao is lower in 5/5 E4 seed comparisons but only 4/23 E5 operation/seed cells.

4. **What is the E4 ordering?** Hsiao has lower vectorless total power in all five matched physical seeds; mean Hsiao-minus-SECDED total-power difference is −0.3147 mW.

5. **What is the E5 ordering?** Hsiao has lower ECC-logic operation energy in 4 of 23 qualified matched operation/seed cells. The 23 cells comprise four idle, five clean-read, four clean-write, five correction, and five detection comparisons.

6. **What is the clean-read delta?** Mean Hsiao-minus-SECDED energy is −0.0308 pJ/op across five matched seeds.

7. **What is the clean-write delta?** +0.1207 pJ/op across four qualified matched seeds.

8. **What is the correction delta?** +0.3095 pJ/op across five matched seeds.

9. **What is the detection delta?** +0.1935 pJ/op across five matched seeds.

10. **How consistent are those results across seeds?** Hsiao is lower for clean read in 3/5 seeds and idle in 1/4; it is lower in 0/4 write, 0/5 correction, and 0/5 detection seeds. Leave-one-seed-out means retain SECDED's lower-energy direction for write, correction, and detection under every omission. The clean-read mean can change sign when one seed is omitted.

11. **What does component decomposition show?** For clean read, Hsiao switching power is lower in 5/5 pairs, internal power is higher in 5/5, and leakage is higher but much smaller in 5/5; combined Hsiao energy is lower in 3/5.

12. **What mechanism is supported?** The component evidence supports an association: lower Hsiao switching contribution coexists with a higher Hsiao internal contribution that partly or fully offsets it.

13. **What mechanism remains inferred?** A gate-, arc-, or logic-cone-level causal explanation for the component changes. No intervention isolates that cause.

14. **What physical tradeoffs exist?** Hsiao adds on average 237.6 µm² total instance area, 237.2 µm² standard-cell area, 2992.8 µm wirelength, and 467.8 vias; every matched delta is positive. Mean setup WNS is 0.2437 ns higher for Hsiao and higher in 4/5 seeds, while both architectures close 10 ns in 5/5 seeds.

15. **How is reliability incorporated?** Validated SECDED correction/detection behavior is a hard admission constraint before ranking. This admits conventional SECDED and Hsiao, excludes unprotected U0, and keeps the evaluated timing-infeasible BCH out of the equal-performance E5 comparison.

16. **Which reliability quantities remain model-based?** Analytical, simulator-derived, or Monte Carlo quantities elsewhere in the repository retain those evidence classes. Physical FIT, Qcrit, SDC, DUE, and physical interleaver behavior are not qualified by this E5 campaign.

17. **How does workload composition change preference?** Positive read weight can make Hsiao lower-energy, whereas idle, write, correction, and detection weights oppose that advantage in the jointly observed four-seed mean. Hence preference is a region in operation-mix space, not an architecture-wide rank.

18. **What is the analytical preference boundary?** For the four complete seeds, `ΔE = 0.019108 p_I − 0.081182 p_R + 0.120682 p_W + 0.256536 p_C + 0.140507 p_D` pJ/op. Hsiao is lower iff `p_R > (0.019108 p_I + 0.120682 p_W + 0.256536 p_C + 0.140507 p_D)/0.081182`. On `p_C=p_D=0`, this is `0.100290 p_I + 0.201864 p_W < 0.081182`.

19. **What Pareto front is qualified?** The architecture-mean `{total instance area, setup WNS, clean-read ECC-logic energy}` front at 10 ns contains both SECDED and Hsiao: SECDED has less area, while Hsiao has higher mean WNS and slightly lower mean clean-read energy.

20. **Is a global winner claimed?** No. The result is `NO_GLOBAL_WINNER_QUALIFIED`.

21. **Is whole-memory energy claimed?** No. It is blocked by incomplete SRAM macro-internal characterization.

22. **Is silicon validation claimed?** No. E5 is a post-route EDA estimate using routed-netlist activity and extracted parasitics.

23. **Is physical FIT claimed?** No.

24. **Is Qcrit claimed?** No.

25. **Is absolute lifecycle carbon claimed?** No. Process-specific embodied/manufacturing carbon is not qualified.

26. **What sustainability conclusions remain defensible?** The qualified ECC-logic operation-energy model can be propagated to an operational-carbon scenario only when operation count, workload probabilities, and electricity carbon intensity are declared. The same ECC-logic boundary must be preserved.

27. **What are the principal statistical limitations?** Five matched placement seeds are implementation replications, not a population sample. Idle/write have only four qualified pairs. Bootstrap intervals and leave-one-out results are descriptive sensitivities; no statistical-significance or manufacturing-population inference is made.

28. **What are the principal physical-design limitations?** One SKY130HD open-source flow, TT/1.80 V/25 °C, 10 ns, five seeds, zero-delay routed-netlist activity, final SPEF, deterministic traces, EDA library/model dependence, and E5 only for SECDED/Hsiao. No 5 ns E5, U0 E5, BCH E5, or silicon result is generalized.

29. **What is the central novelty claim after literature audit?** A matched, evidence-qualified empirical test of whether a vectorless Hamming/Hsiao ordering survives operation-separated final-routed activity with extracted parasitics, coupled to a transparent workload preference boundary. This is bounded to the literature located in the focused audit and is not a priority claim.

30. **Which candidate novelty claims were rejected?** A new ECC code, new Hsiao construction, new activity-power method, new OpenROAD flow, new workload-aware/adaptive ECC concept, new Pareto method, optimal ECC, global winner, and absolute semiconductor-lifecycle-carbon result.

31. **Which manuscript claims are `SUPPORTED_WITH_SCOPE`?** Ledger claims C01, C03, C05–C13, C16–C18, and C27. Their scope conditions include matched seed counts, 10 ns, final-routed EDA estimation, operation class, ECC-logic boundary, and declared scenario assumptions. C14 and C20 are separately marked `MODEL_DEPENDENT`, and C15 is `ANALYTICAL_ONLY`.

32. **Are any `FATAL_EVIDENCE_GAP`s present?** None for the narrowed research question and conclusion. Whole-memory energy, physical FIT/Qcrit/SDC/DUE, other timing/PVT conditions, U0/BCH E5, silicon validation, and absolute lifecycle carbon would be fatal only to broader claims that the manuscript does not make.

33. **Can each fatal gap instead be handled by narrowing a claim?** Yes for this paper. Every absent dimension is stated as an exclusion or limitation and is omitted from the qualified comparison.

34. **Is another experiment genuinely necessary?** No major experiment is necessary to support the stated 10 ns, two-architecture, ECC-logic result. Broader external-validity claims would require new evidence, but they are not needed for this argument.

35. **Is the paper ready for ISCAS drafting?** Yes at the scientific-draft level: the claim ledger, generated analyses, figures, table, manuscript, provenance, and audits agree. Final IEEE template typesetting, author metadata, and the released ISCAS 2027 author-kit check remain production work.

36. **Which four figures/tables should survive the page-budget cut?** Keep Figure 1 (GREEN sequence), Figure 2 (E4 versus E5 counts), Figure 3 (paired operation deltas), and Figure 4 (workload boundary). Compress the primary physical/energy table into the results text or replace Figure 1 with that table if typesetting pressure demands one trade.

37. **What evidence should remain in supplementary/repository material rather than the four-page manuscript?** All 46 provenance rows; per-seed physical and energy tables; bootstrap resamples and leave-one-out values; hash-verification details; toolchain strings; failed OpenRAM chronology; and U0/BCH evidence beyond concise exclusion reasons.

38. **What final commit seals the analysis?** The evidence input is sealed by `8cf245ac6ac8cb9b010c073d439f04eb204d48a1`. The analysis state is sealed by the commit referenced by tag `iscas2027-green-operation-aware-v1`; its exact object ID is reported at handoff rather than embedded self-referentially in that commit.
