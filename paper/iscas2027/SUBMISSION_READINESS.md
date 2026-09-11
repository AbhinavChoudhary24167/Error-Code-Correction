# ISCAS 2027 Submission Readiness

## Current disposition

**Technically complete draft; not yet author-submission-ready.** The evidence,
analysis, manuscript, references, build, and visual checks are complete. Two
author-owned blockers remain: real author metadata and a publication-overlap
decision concerning the adjacent DATE activity manuscript.

## Venue and format verification

Checked on 2026-09-10 against the official [ISCAS 2027 site](https://2027.ieee-iscas.org/),
[submission author information](https://epapers2.org/iscas2027/ESR/authorinfo1.php),
and [official sample/template page](https://epapers2.org/iscas2027/ESR/samples.php):

- Venue: IEEE ISCAS 2027, Bordeaux, France, 6--9 June 2027.
- Regular-paper deadline shown by the official site: 13 October 2026.
- Review is not double-blind; author names and affiliations belong in the PDF.
- Maximum length is five pages total: up to four pages including technical text,
  figures, and tables; an optional fifth page may contain references only.
- US Letter or A4 is accepted; the artifact uses US Letter.
- IEEE conference formatting is required; the artifact uses `IEEEtran` in
  conference mode.
- Fonts must be embedded and Type 3 fonts are prohibited.
- The submitted PDF must be at most 5 MB and must not be encrypted or secured.

Artifact checks:

- `main.pdf`: five pages; pages 1--4 technical content, page 5 references only.
- File size: approximately 0.26 MB, below the 5-MB limit.
- Page size: 612 x 792 points (US Letter).
- Encryption: none.
- Font audit: every listed font is embedded; no Type 3 fonts.
- LaTeX: no fatal errors, unresolved citations/references, multiply defined
  labels, or overfull boxes. Remaining underfull-box notices are non-fatal and
  visually benign.
- Visual QA: all five rendered pages inspected at 150 dpi; plots, tables,
  equations, captions, and references are legible and unclipped.
- Paper validator: PASS (16 claim-provenance rows, five pages, no source-hash
  drift).
- Repository build: `make` PASS.
- Repository test target: `make test` reports 482 passed and two failures in the
  legacy Gate03 working-tree scope allowlist. The dirty campaign tree (and the
  newly requested paper path) lies outside that historical allowlist.
- Full Python suite: `python3 -m pytest -q` reports 718 passed and five failures.
  Two are the same Gate03 scope failures; the remaining three are pre-existing
  frozen-campaign/hash mismatches in attempt10 activity, the refoundation final
  hash manifest, and the modified GREEN v3.2 frozen tree. None exercises or
  contradicts the paper generator, provenance, or PDF.

## MUST DO before submission

1. Replace the author placeholder with complete names, affiliations, and email
   addresses. The official process is not double-blind.
2. Resolve the **HIGH** overlap with
   `campaigns/date_2027_activity_qualified_ecc_energy_rev2/DATE2027_MANUSCRIPT_REV2.tex`.
   Do not submit both materially unchanged. See `DATE_OVERLAP_AUDIT.md`.
3. Have every listed author verify the evidence, equations, citations, figures,
   conclusions, and repository state. Then change the AI-disclosure sentence
   from “must verify” to a truthful completed-action statement.
4. Confirm the final IEEE/ISCAS policy for AI-assisted text at submission time.
   The draft includes a disclosure based on the current official
   [IEEE guidance](https://open.ieee.org/author-guidelines-for-artificial-intelligence-ai-generated-text/).
5. Add funding acknowledgments, conflicts, author permissions, and any required
   companion-paper disclosure. Do not invent them.
6. Recheck the official deadline, template, PDF validation instructions, and
   paper-category requirements immediately before upload; venue pages can change.
7. Run the venue's PDF validation/PDF eXpress step when its conference account is
   available, and upload only the validated PDF.
8. Reconcile or isolate the dirty campaign worktree before creating a submission
   tag. Do not regenerate frozen seals blindly; determine whether the modified
   evidence is intentional, then either preserve it on a separate branch or
   update provenance through the campaign's authorized sealing procedure.

## HIGH VALUE

- Obtain a same-boundary SRAM macro characterization with address/data/state-
  dependent internal energy. This would turn ECC-logic E5 into a qualified
  whole-memory comparison.
- Implement and qualify a latency-aware pipelined BCH memory wrapper rather than
  generalizing from the current unpipelined timing failure.
- Add delay-aware gate activity or explicitly quantify zero-delay VCD bias.
- Supply a deployed workload distribution and report sensitivity instead of
  treating operation fractions only as variables.
- If lifecycle conclusions are desired, build a matched SKY130 manufacturing
  inventory with declared geography, yield, process-gas, abatement, allocation,
  and system boundaries.

## OPTIONAL

- Add a public artifact DOI or archival release tag after sanitizing repository
  paths and confirming redistribution rights for SRAM/PDK collateral.
- Add color-vision-deficiency and grayscale proofs for the plots.
- Add a one-paragraph artifact-availability statement if allowed by the final
  author kit.
- Replace abbreviated author lists in BibTeX with complete metadata for entries
  currently using `and others`.

## Not qualified and intentionally absent

- whole-memory or SRAM-macro E5 energy;
- silicon-measured power, Qcrit, FIT, SDC, DUE, lifetime, or radiation response;
- physical interleaver benefit or numerical MBU rate;
- numerical SKY130 embodied/manufacturing carbon;
- a global greenest/optimal ECC claim;
- statistical inference from deterministic route seeds.
