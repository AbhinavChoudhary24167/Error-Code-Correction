# ISCAS 2027 Internal Review

## Review disposition

Six hostile reviews were conducted against the manuscript, audits, generated
artifacts, and rendered PDF. The technical package is internally consistent and
appropriately scoped. The submission remains gated by author metadata and the
adjacent DATE activity-paper overlap decision.

## Reviewer 1 — Experimental methodology

**Objection.** The activity campaign has 46 E5 records, but seed 11 is incomplete
for idle/write and Hsiao also has a hold violation. Using all available values
would create class-dependent sample sizes and violate full timing comparability.

**Response/action.** The generator derives a primary complete-case cohort only
when both SECDED implementations have nonnegative setup and hold WNS and all five
operation classes. This produces seeds 13, 17, 19, and 23, 40 E5 records, and 20
paired cells. Seed 11 remains documented as sensitivity evidence but is excluded
from every primary coefficient.

**Verdict.** PASS. The selection rule is evidence-based and encoded before
aggregation. No p-values or confidence intervals are claimed.

## Reviewer 2 — Physical-design/CAD validity

**Objection.** “Post-route” can conceal mismatched netlists, parasitics, activity,
or macro assumptions; zero route DRC errors are not equivalent to signoff.

**Response/action.** The campaign preserves result/VCD/netlist/SPEF/workload
hashes, the final routed-netlist zero-delay activity boundary, the pinned
ORFS/OpenROAD/SKY130HD identity, and matched seeds. The manuscript says “zero
reported route-DRC errors,” not signoff. It reports setup and hold separately,
does not call 5-ns results feasible, and excludes the incomplete OpenRAM attempt
from all claims.

**Residual concern.** Zero-delay VCD omits delay-induced glitch activity and the
upstream SRAM22 views lack independent full signoff.

**Verdict.** PASS WITH EXPLICIT LIMITATION.

## Reviewer 3 — Reliability claims

**Objection.** Categorical SECDED/BCH behavior can be overread as radiation
reliability, and interleaving can be asserted without physical adjacency data.

**Response/action.** The paper binds guarantees to named RTL identities and their
formal/regression boundaries. It never converts code service into Qcrit, FIT,
SDC, DUE, lifetime, or avoided faults. It cites topology literature precisely to
explain why the absent physical-to-logical bit map blocks numerical MBU claims.
SEC--DAEC and unimplemented interleavers fail closed.

**Verdict.** PASS.

## Reviewer 4 — Sustainability/LCA claims

**Objection.** Advanced-node literature and ACT coefficients could be silently
reused as SKY130 manufacturing carbon, producing a false numeric lifecycle win.

**Response/action.** The manuscript uses external sustainability work only for
model structure and boundary discipline. It gives a dimensionally audited
symbolic lifecycle equation and conditional break-even, explicitly states that
the SKY130 inventory is missing, and reports no absolute carbon number or global
winner.

**Verdict.** PASS. This is conservative but scientifically defensible.

## Reviewer 5 — Reproducibility and quantitative traceability

**Objection.** Hand-entered figure coefficients and abstract numbers could drift
from campaign data; undocumented source changes could invalidate the paper.

**Response/action.** One deterministic script reads the five authoritative
campaign artifacts and emits figures, tables, LaTeX macros, derived JSON, and
claim-level provenance. `RESULT_PROVENANCE.csv` stores source paths, SHA-256
hashes, formulas, evidence levels, units, and qualification boundaries. The
manuscript consumes generated macros for every headline number.

**Verdict.** PASS, subject to rerunning the validator after any source change.

The paper validator passes. Repository-wide regression is not fully green:
`make` passes; `make test` yields 482 passes/two worktree-scope failures; and the
full `python3 -m pytest -q` yields 718 passes/five failures. The additional full-
suite failures are immutable-source/final-manifest checks against already
modified campaign evidence. They do not test the paper, but they block a claim
that the whole repository is clean and must be resolved or isolated before a
submission release tag.

## Reviewer 6 — Novelty, venue fit, and submission ethics

**Objection.** The tracked DATE paper already owns the identity-preserving
physical-outcome thesis, while an adjacent DATE draft uses the same activity
records and workload crossover. The current author block is also a placeholder.

**Response/action.** The new paper rejects the tracked DATE novelty and centers
fail-closed cross-layer admission, stronger-code timing infeasibility, and
missingness-preserving lifecycle decisions. This sufficiently separates it from
the tracked DATE Revision 3. It does **not** eliminate the high overlap with the
adjacent activity DATE draft; simultaneous submission unchanged is prohibited by
the readiness audit. Official ISCAS rules were checked, and the manuscript uses
four technical pages plus a references-only fifth page with embedded fonts.

**Verdict.** TECHNICAL PASS / SUBMISSION BLOCKED until real author metadata is
inserted and the DATE activity overlap is resolved and disclosed.

## Final consensus

- Evidence discipline: strong.
- Quantitative reproducibility: strong.
- Reliability and LCA scope: appropriately conservative.
- Physical generalization: limited to one named implementation flow, as stated.
- Novelty relative to tracked DATE Revision 3: defensible.
- Novelty/publication separation relative to adjacent DATE activity draft:
  unresolved high risk.
- Format and visual quality: pass.
- Whole-repository clean-test claim: blocked by the pre-existing dirty campaign
  and historical allowlist, despite the paper-specific validator passing.
- Overall: **complete research draft, not yet upload-ready for author-owned
  administrative and overlap reasons**.
