# Activity-qualified ECC energy evidence report

## Scope

This package evaluates whether the relative energy ordering of matched conventional and Hsiao SECDED implementations changes when a vectorless estimator is replaced by operation-specific switching activity. The measurement boundary is routed ECC logic around the memory interface; SRAM-macro internal energy and silicon behavior are excluded.

## Retained results

- Ten 10 ns implementations route and meet setup timing across five matched seeds per architecture.
- The dataset contains 46 admitted activity records and 23 matched architecture/seed/operation cells.
- Vectorless total logic power favors Hsiao in 5/5 matched pairs.
- Operation-specific ECC-logic energy favors Hsiao in 4/23 matched cells.
- Every admitted record covers all 72 output activity roots, with 16 warm-up cycles and 256 measured operations.
- Component accounting shows that internal and switching contributions can oppose one another; the accounting supports, but does not prove, a causal explanation for total-energy signs.

## Evidence and limits

The canonical numerical inputs are under `data/`; regenerated summaries are under `tables/` and `figures/`. `DATE2027_CLAIM_LEDGER.md` records qualification and limitations, and `PROVENANCE_MANIFEST.json` records file hashes.

The results are conditional on the evaluated flow, library, corner, workload classes, and deterministic seeds. They do not establish a universal ECC winner, whole-memory energy, population significance, physical event rates, or silicon behavior.

Publication manuscripts, review material, and submission PDFs are not part of this repository.
