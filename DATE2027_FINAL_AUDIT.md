# DATE 2027 final manuscript audit

## Title

Implementation Identity Matters: Post-Route Trade-offs in Memory ECC Hardware

## Abstract

Error-correcting-code (ECC) capability alone does not determine whether a protection scheme is practical in hardware. Algorithm-level comparisons omit microarchitectural latency and the area, timing, routing, and energy effects introduced during physical implementation. We present an identity-preserving evaluation method that admits correctness-qualified ECC implementations, separates guaranteed correction from exhaustive out-of-guarantee observations, and characterizes accepted RTL under one pinned post-route flow. In SKY130HD, two temporally aligned exact-equivalent SECDED (72,64) implementations occupy non-dominated points: relative to the combinational design, pipelining increases standard-cell area by 36.702% and adds two cycles of request latency, but raises achieved Fmax by 45.911% and reduces steady-stream energy per operation by 24.016%. The evaluated shortened BCH (78,64,t=2) implementation corrects all weight-2 errors but uses 207.356% more area than combinational SECDED and misses the common 10 ns target. These results are specific to the evaluated RTL, technology, corner, and physical policy. They show why reliable selection must preserve implementation identity, timing feasibility, and missing evidence rather than infer physical quality from coding strength.

## Contributions

1. An identity-preserving cross-layer evaluation method that admits correctness-qualified ECC implementations and keeps guarantees, observations, architecture, and unavailable physical data distinct.
2. A quantified non-dominated post-route trade-off between two exact-equivalent SECDED microarchitectures.
3. An implementation-scoped correction-versus-feasibility result for the evaluated BCH RTL, while retaining unavailable Hsiao PPA explicitly rather than estimating it.

## Figures

1. Identity-preserving evaluation workflow, including the insufficient-evidence side path.
2. Post-route standard-cell area versus achieved Fmax for the two SECDED implementations and BCH, including the 100 MHz target and no artificial Hsiao point.
3. Normalized two-panel trade-offs: all routed physical metrics, then power/energy only for timing-feasible SECDED points.

All figure PDFs and CSV inputs are generated from frozen evidence by `paper/date2027/scripts/build_artifacts.py`; source keys and transformations are recorded in `paper/date2027/data/traceability.json`.

## Tables

1. Implementation identities, guarantees, latency, II, payload, and physical status, retaining Hsiao as `PPA unavailable`.
2. Post-route results, retaining BCH power as diagnostic and omitting BCH target-clock energy.

Both tables are generated from the frozen Gate 07 CSV evidence, with their generated CSV mirrors and transformation record in the manuscript package.

## Page count

- Manuscript: 6 pages.
- References-only allowance: 1 page.
- Total PDF: 7 pages, US Letter, double column, 10 pt, no page numbers.

## Reference count

15 references, all cited in the manuscript. Bibliographic identities were checked against publisher/DOI records, proceedings, or the cited primary preprint. The focused external audit contains 16 close-work records and the positioning decision.

## Numerical-validation status

**PASS.** The semantic validator checks all nine required headline quantities against `GATE07_MANUSCRIPT_EVIDENCE.json`: 36.702%, 12.067%, 45.911%, 24.016%, 207.356%, 310.975%, 72.258%, -4.78052 ns, and 67.6566 MHz. BCH target-clock energy is prohibited and absent.

## Repository verification

- `make`: **PASS**.
- `make test`: **477 passed, 2 failed**. The two failures are the historical Gate 03 working-tree scope checks, which reject required Gate 08 files and many pre-existing later-gate/untracked paths as outside their frozen allowlist.
- `python3 -m pytest -q`: **479 passed, 2 failed** with the same two Gate 03 scope-policy failures.

The failing assertions do not exercise manuscript generation, numerical claims, LaTeX, figures, references, or the submission PDF. Their validator allowlists were not broadened because this task prohibits changes to frozen prior-gate policy and unrelated workspace content.

## Known limitations

- Specific evaluated RTL implementations only.
- SKY130HD at TT 1.80 V / 25 C only.
- One common 10 ns target and one deterministic seed/worker policy; no seed distribution, process variation, or multi-corner signoff.
- Hsiao PPA unavailable under the unchanged 4096-bit synthesis-memory policy.
- BCH target-clock energy excluded because the evaluated implementation misses 10 ns.
- OpenSTA activity-based power estimates, not silicon measurements.
- No FIT, SER, field weighting, physical SRAM array mapping, interleaving, or scrubbing model.
- Three routed designs and two timing-feasible energy points.

## Remaining submission actions

- Enter authors, affiliations, topics, conflicts, and other metadata in the DATE submission portal; keep the PDF anonymous for double-blind review.
- Upload `output/pdf/date2027_submission.pdf` and complete any portal-provided PDF/compliance check.
- Confirm the portal's final administrative deadline and submission-category selections.

These are administrative submission actions, not manuscript or evidence blockers.
