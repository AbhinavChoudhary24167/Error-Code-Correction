# DATE / ISCAS 2027 Overlap Audit

## Scope

This audit compares the new ISCAS manuscript with every adjacent manuscript or
draft in the repository that uses the same ECC identities or campaign chain. It
is a technical overlap review, not legal advice and not a substitute for the
authors' disclosure obligations to either venue.

## Compared artifacts

1. `paper/date2027_revision3/date2027_revision3.tex` — tracked DATE manuscript,
   *From ECC Semantics to Physical Outcomes: Identity-Preserving Evaluation of
   Memory ECC Hardware*.
2. `campaigns/date_2027_activity_qualified_ecc_energy_rev2/DATE2027_MANUSCRIPT_REV2.tex`
   — adjacent activity-qualified DATE draft, *When ECC Energy Ordering Depends
   on Activity*.
3. `paper/iscas2027_green_operation_aware/` — older ISCAS-oriented draft,
   *When Vectorless Power Ordering Does Not Survive Operation-Aware Activity*.
4. `paper/iscas2027/main.tex` — manuscript audited here.

## Claim-level matrix

| Axis | Tracked DATE Revision 3 | Adjacent DATE activity draft | New ISCAS manuscript | Overlap verdict |
|---|---|---|---|---|
| Central question | How semantic, architectural, and physical identity affect conclusions | Whether vectorless Hamming/Hsiao ordering survives routed activity | Which preferences remain identifiable after service, full timing, activity, and lifecycle evidence gates | Distinct from tracked DATE; related to activity DATE. |
| Main novelty | Identity-preserving equivalence across combinational/pipelined and flat/hierarchical ECC forms | Vectorless-to-activity ordering change and operation/workload crossover | Fail-closed cross-layer admission, stronger-code infeasibility, missingness-preserving decision surface, symbolic lifecycle boundary | ISCAS wording deliberately avoids the tracked DATE novelty. |
| Main population | Equivalent implementation variants plus matched physical outcomes | Conventional vs Hsiao SECDED E5 activity population | U0, conventional SECDED, Hsiao SECDED, BCH; E5 narrowed to four full-timing-clean SECDED pairs | Partial population overlap. |
| Shared physical evidence | 10/5-ns matched routed seeds | Same campaign chain for SECDED/Hsiao | Same campaign chain; derives setup+hold-clean primary cohort | Data reuse must be disclosed. |
| Shared energy evidence | Not central | Central E5 operation records | Same E5 records are one component of a broader admission argument | High quantitative overlap with adjacent DATE activity draft. |
| Shared conclusion | Physical outcome depends on exact implementation identity | Energy ordering depends on activity/operation mix | No architecture preference is admissible before service, timing, and boundary gates; workload sign remains conditional | Conceptually separable, but some result sentences are close. |
| Lifecycle/carbon | Not central | Limited/secondary | Symbolic operational/embodied break-even and strict node-boundary refusal | Primarily ISCAS-specific. |

## Deliberate separation in the new manuscript

- It does not claim that equivalent RTLs can have different physical outcomes;
  that is the tracked DATE thesis.
- It does not use vectorless-to-activity ranking reversal as its central result;
  that is the adjacent DATE activity thesis.
- It admits the unprotected and BCH identities to demonstrate categorical
  service and timing gates, then restricts energy to the equal-service,
  full-timing-clean SECDED cohort.
- It makes missing SRAM energy, physical fault rates, and SKY130 embodied carbon
  part of the decision result rather than filling them with external proxies.
- No prose is copied from either DATE manuscript. Shared facts are regenerated
  from the same frozen source records and traced in `RESULT_PROVENANCE.csv`.

## Residual risk

**Tracked DATE Revision 3: LOW-to-MODERATE overlap.** The repository, tools,
architectures, and some physical records overlap, but the research question,
comparison population, primary claims, and conclusion differ. A related-work or
companion-paper disclosure should still identify the shared campaign lineage.

**Adjacent DATE activity Revision 2: HIGH overlap.** It uses the same E5 records,
operation classes, and workload crossover that appear in the ISCAS results.
Although the ISCAS manuscript embeds these within a broader evidence-admission
argument and adds U0/BCH/lifecycle gates, simultaneous submission of both drafts
without explicit cross-citation, disclosure, and substantial differentiation
would create a serious duplicate-publication risk.

**Older ISCAS operation-aware draft: SUPERSEDED.** It is not an independent
submission candidate if the new manuscript proceeds. Archive it as internal
history or clearly mark it superseded.

## Required author decision

Do not submit the new ISCAS manuscript while the adjacent DATE activity draft is
also under consideration in materially unchanged form. Before submission, the
authors must choose one of the following defensible paths:

1. submit only one activity-energy paper and treat the other as internal work;
2. substantially separate experiments and claims, then cross-cite/disclose the
   companion submission according to both venues' policies; or
3. withdraw or defer one manuscript.

This unresolved choice is classified as a **MUST DO** item in
`SUBMISSION_READINESS.md`.

