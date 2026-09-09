# Paper outline and page-budget design

## Research question

Can an ECC architecture preference inferred from reliability and conventional vectorless physical-design power remain valid when matched post-route implementations are evaluated using operation-specific switching activity?

## Working title

**When Vectorless Power Ordering Does Not Survive Operation-Aware Activity: A Matched Post-Route SRAM-ECC Study**

## Argument, not chronology

1. Both evaluated `(72,64)` implementations meet the same coding-theoretic SECDED requirement and the 10 ns timing constraint.
2. The inherited vectorless E4 diagnostic favors Hsiao in all five matched seeds.
3. Final-routed, operation-specific E5 activity preserves that ordering in only 4 of 23 matched operation/seed cells.
4. The direction depends on operation mix. A clean-read benefit exists on average, while write, correction, and detection favor SECDED in every qualified seed.
5. GREEN therefore returns admissible alternatives, qualified Pareto sets, and a workload boundary—not a global scalar winner.

## Four technical pages plus references-only page

| Section | Target share | Purpose | Visual allocation |
|---|---:|---|---|
| Abstract | 150–180 words | Question, method, 5/5 versus 4/23 result, ECC-logic boundary | none |
| I. Introduction and related work | 0.55 page | Establish activity-dependent comparison and bounded gap | none |
| II. GREEN methodology | 0.70 page | Qualification, constraints, operation vector, workload equation, Pareto policy | Fig. 1 |
| III. Experimental methodology | 0.60 page | Matched architectures/seeds, 10 ns, post-route VCD+SPEF, 16+256 protocol, exclusions | compact text |
| IV. Results and discussion | 1.55 pages | Physical tradeoff, E4→E5 ordering, paired operation deltas, component decomposition, workload boundary | Figs. 2–4 and one compact table |
| V. Limitations and conclusion | 0.35 page | Exact established result and consequences of every principal boundary | none |
| References | 1 page | Focused primary literature | references only |

## Contributions retained after literature audit

1. An evidence-qualified decision method that applies reliability and timing constraints before comparing jointly qualified physical and operation-aware quantities.
2. A matched five-seed post-route result: the Hsiao-lower vectorless ordering in 5/5 seeds remains Hsiao-lower in only 4/23 operation/seed E5 comparisons.
3. A workload formulation and measured coefficient set that exposes the Hsiao/SECDED energy-preference boundary without assigning hidden probabilities.

These are bounded method and empirical contributions. The paper does not claim the Hsiao construction, workload-aware ECC, activity-based power analysis, Pareto analysis, or semiconductor sustainability accounting as new.

## Material kept out of the four-page body

- all 46 provenance rows;
- bootstrap resamples and leave-one-seed-out values;
- complete physical per-seed tables;
- failed OpenRAM chronology;
- U0 and BCH E4 details beyond the exclusion reason;
- analytical reliability scenario campaigns unrelated to the research question;
- carbon defaults or proxy embodied-carbon estimates.
