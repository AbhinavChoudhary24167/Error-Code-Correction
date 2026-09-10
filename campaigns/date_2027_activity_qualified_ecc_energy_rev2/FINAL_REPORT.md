# DATE 2027 Rev. 2 Final Report

## Outcome

The additive Rev. 2 package preserves the current activity-aware paper and restores earlier experiments only as controls. The central remembered result remains: under the evaluated 10-ns post-route conditions, Hsiao is lower in 5/5 vectorless physical pairs but only 4/23 operation-specific energy cells.

## Scientific checks

- Main study: 10 timing-feasible routed implementations, five matched deterministic seeds per architecture, 46 activity records, and 23 matched operation/seed cells.
- Exact final-route association: each activity result is joined to architecture, seed, routed netlist, final SPEF, workload/VCD, and result digest.
- Coverage: all 72 output activity roots; functional logic coverage 99.298390--99.356061%; 16 warm-up cycles and 256 measured operations.
- Measurement boundary: routed ECC logic; SRAM-macro internal energy and silicon claims excluded.
- Component accounting retained centrally: clean-read internal +25.890767574 uW and net switching -28.973363806 uW, each sign 5/5; correction and detection details are regenerated in `data/component_power_summary.csv`.
- Temporal SECDED control: pair-specific exact systematic transaction relation after two-cycle response alignment; latency 1 vs 3, II=1. At 10 ns, area +37.201864%, timing +46.629355%, energy -23.419005%; directions 5/5.
- Condition control: the same temporal pair at 5 ns gives area +36.721138%, timing +68.629653%, energy -19.336606%; this is not a 5-ns replication of the headline conventional/Hsiao activity result.
- Structural Hsiao control: exact arbitrary-word decoder equality and same-cycle temporal behavior; small mixed area/wire/via/timing/energy displacement.
- Feasibility boundary: the evaluated BCH(78,64,t=2) syndrome/Chien realization meets the common 10-ns target in 0/5 attempts; no BCH-family claim is made.

## Literature and claim checks

Fifteen cited works are audited: fourteen DOI-bearing publications and one verified arXiv preprint. Ghosh, Basu, and Touba 2004 already performs trace-aware Hamming/Hsiao checker-power comparison, so the contribution is not framed as the first activity-aware ECC analysis. The retained novelty statement is the narrower matched final-route, preserved-parasitic estimator-ordering test. The claim ledger uses only the allowed scoped statuses and records source, role, qualification, limitation, and literature support.

## Manuscript and visual checks

- The title is retained because it names Q3 directly and remains distinct from the previous identity-focused manuscript.
- Q1/Q2 occupy a single controlled-implementation table and bounded discussion; Q3 receives all four figures and most quantitative analysis.
- Figure 1 shows the full nine-stage evidence chain and separates hardware/temporal, implementation/physical, and activity/measurement dimensions.
- Figures 2--4 retain the ordering matrix, all operation deltas, and component decomposition.
- Baseline, revised, candidate, analysis-only, and historical visuals plus their source data/scripts are preserved and classified.
- Reader-facing prose omits internal campaign/version labels.

## Deliverables

All files requested in the revision brief are present in this directory, including the Markdown and LaTeX manuscripts, bibliography, formal matrix, control evidence, current/previous audits, literature and reference audits, claim/reproducibility ledgers, figure/table manifests, visual reviews, page/blind/citation audits, reviewer attacks, fatal-gap report, build/validation scripts, PDF, and content-sealed provenance manifest.

## Release status

`DATE_MANUSCRIPT_PACKAGE_READY: YES`

`DATE_SUBMISSION_READY: NO` until the authors complete author metadata, policy declarations, and portal submission.
