# DATE 2027 submission readiness

Assessment date: 2026-09-10  
Primary topic: D9 — Low-power, energy-efficient and thermal-aware design  
Secondary topic: D13 — Physical analysis and design

## Required readiness questions

1. **What is the final research question?**  
   After behavioral qualification, how much can semantics-preserving changes
   to ECC hardware architecture alter physical and energy outcomes, and which
   observed trade-offs remain consistent across matched physical-design
   perturbations and a tighter implementation constraint?

2. **What are the maximum three contributions?**

   1. A fail-closed, machine-auditable formal-to-physical admissibility method
      joining code identity, hardware/transaction identity, physical identity,
      target feasibility, activity, and result provenance.
   2. Two exact-equivalence contrasts that isolate temporal SECDED
      restructuring from latency/II/state-preserving structural Hsiao
      restructuring and expose very different physical effect scales.
   3. Matched-seed plus fresh 5 ns evidence for the temporal trade directions,
      with component-level accounting showing that switching is the largest
      reported contributor to the 10 ns energy difference.

3. **Why is D9 the primary topic?**  
   The principal result is an implementation- and activity-conditioned energy
   trade-off: the pipelined SECDED identity uses 23.4% less energy per useful
   operation at 10 ns while paying area and request-latency costs. The paper
   foregrounds workload qualification, power components, energy normalization,
   and the conditions under which that ordering persists.

4. **Why is D13 the secondary topic?**  
   Every energy and timing conclusion is tied to matched routed physical
   identities, fixed library/corner/floorplan policy, deterministic route-seed
   perturbations, extracted parasitics, and explicit setup/hold/DRC gates.
   Physical analysis is therefore constitutive evidence, although the paper
   does not contribute a new physical-design algorithm.

5. **What exact comparisons are formally equivalent?**  
   The combinational and pipelined SECDED (72,64) pair is transaction-equivalent
   after the documented two-cycle response alignment (request latency 1 versus
   3, II=1). The flat and hierarchical Hsiao pair has arbitrary received-word
   decoder equivalence and same-cycle registered-boundary temporal induction
   from the specified all-zero initialization under arbitrary reset, valid,
   payload, and received-word sequences (latency 1 and II=1 for both). BCH is
   not presented as formally equivalent to either family.

6. **What experimental results were preserved from the previous manuscript?**  
   All five required families: 10 ns temporal SECDED; 10 ns structural Hsiao,
   including its small effects and timing reversal; 10 ns SECDED power
   decomposition; fresh 5 ns SECDED replication; and the BCH(78,64,t=2)
   feasibility boundary. Latency, II, seed directions, physical feasibility,
   unfavorable component movements, and energy-ineligibility rules are also
   retained.

7. **What results changed, and why?**  
   No qualified numerical result changed and no supported result was removed.
   Display values are regenerated from full-precision frozen artifacts. The
   prose now states proof and workload boundaries more exactly, and Fig. 3(a)
   uses absolute mW differences so the top-level and cell-group accounting is
   additive rather than visually comparing percentages with different
   denominators.

8. **How many physical runs support each headline claim?**

   | Headline family | Physical evidence |
   |---|---:|
   | SECDED temporal comparison, 10 ns | 10 routed runs: 5 matched seed pairs |
   | Hsiao structural comparison, 10 ns | 10 routed runs: 5 matched seed pairs |
   | SECDED power decomposition, 10 ns | the same 10 qualified SECDED routed/power points |
   | SECDED tighter-target replication, 5 ns | 10 fresh routed runs: 5 matched seed pairs |
   | BCH feasibility boundary, 10 ns | 5 routed runs |

   Seeds are deterministic physical-heuristic perturbations, not statistical
   samples or process corners.

9. **Are all physical targets correctly classified as feasible/infeasible?**  
   Yes. Both SECDED identities are target-feasible in 5/5 seeds at both 10 ns
   and 5 ns. Both Hsiao identities are target-feasible in 5/5 seeds at 10 ns.
   The evaluated BCH identity is target-infeasible in 5/5 seeds at 10 ns;
   route-complete physical quantities remain reportable, but target-clock
   energy is excluded.

10. **Is all energy trace-qualified?**  
    Yes. Each reported energy comparison joins the qualified routed database,
    parasitics, and identical SplitMix64 trace (seed 104375203646206): six
    reset cycles, 100,000 accepted no-error operations at saturated II=1, and
    four drain cycles. The denominator is useful operations. The manuscript
    explicitly excludes idle, bursty, clock-gated, and correction-heavy scope.

11. **Are power-mechanism statements causal or only accounting?**  
    Accounting only. Switching has the largest reported absolute top-level
    decrease and numerically accounts for the net direction, but the aggregate
    reports cannot distinguish glitch suppression from input activity,
    capacitance, buffering, or placement. No per-net causal mechanism is
    claimed.

12. **Is BCH phrased at the correct scope?**  
    Yes. It is one qualified syndrome/Chien BCH(78,64,t=2) hardware identity
    that misses the common 10 ns target; the manuscript does not infer that BCH
    is inherently slow, impractical, or universally inferior. It is a
    stronger-correction feasibility boundary, not an exact-equivalence or
    target-clock energy comparison.

13. **Is Hsiao's small effect retained?**  
    Yes. Hierarchical versus flat remains reported as area -0.564%, cells
    +0.276%, wire +3.867%, vias +3.918%, timing metric +2.656%, and energy/op
    +1.328%. Its scale is shown without graphical magnification to the SECDED
    effect scale.

14. **Is the one Hsiao timing reversal retained?**  
    Yes. Timing ordering holds in 4/5 matched seeds, and the one reversal is
    stated in the text/table rather than averaged away.

15. **Are negative results retained?**  
    Yes. The BCH 0/5 feasibility result, the Hsiao timing reversal, the small
    Hsiao displacement, the SECDED area/latency costs, and the unfavorable
    internal/leakage/sequential/clock power movements all remain visible.

16. **Are all numbers provenance-linked?**  
    Yes. `RESULT_PROVENANCE.csv` contains 307 rows covering 67 claim IDs, with
    experiment identities, conditions, seed, metric, raw/display value, unit,
    source artifact, source hash, and qualification status. The builder checks
    14 frozen evidence sources and generates 94 LaTeX value macros.

17. **Are all references verified?**  
    Yes at the repository audit level. All 27 entries are cited exactly; 25 DOI
    records inherit the completed Revision-3 identifier/metadata audit, and the
    two primary arXiv records were rechecked on 2026-09-10. A final human
    publisher-format spot-check remains prudent in the submission portal proof.

18. **Is double blindness preserved?**  
    Yes. The author block is anonymous; no author, affiliation, grant, project
    acknowledgment, or identifying PDF metadata is present. The required AI-use
    disclosure names the system and scope without identifying the authors.

19. **Are pages 1-6 technical content only?**  
    Yes for the DATE page budget: all manuscript sections, figures, tables,
    conclusion, and the required anonymous AI disclosure are confined to pages
    1-6. No bibliography spills onto those pages.

20. **Is page 7 references only?**  
    Yes. Text extraction confirms that page 7 starts with `REFERENCES` and
    contains no abstract, introduction, conclusion, acknowledgment, or other
    manuscript section.

21. **Are all figures legible?**  
    Yes. The final seven-page render was inspected page by page; plot labels use
    print-scale fonts, tables use normal 10-point document text, scales preserve
    effect-size contrast, and no overlap or layout-affecting overfull box
    remains. All PDF fonts are embedded and none is Type 3.

22. **What is the strongest remaining reviewer vulnerability?**  
    Reviewer valuation of novelty: the fail-closed identity/provenance protocol
    may be judged as unusually rigorous experimental practice rather than a new
    design methodology. The most material empirical scope limitation behind
    that risk is that the energy headline uses one saturated, primary-input,
    no-error trace rather than a memory-subsystem workload envelope.

23. **What single improvement would most increase acceptance probability?**  
    Add one prospectively frozen, matched second workload campaign that includes
    idle/bursty and correction-active phases while preserving equal useful work,
    complete pipeline drain, identical evidence joins, and the current
    feasibility gate. This would directly test the most vulnerable D9 scope
    boundary without changing the paper's thesis.

## Automated artifact gate

- Revision validator: **PASS**
- Page budget: **PASS** (six technical pages plus one references-only page)
- Bibliography closure: **PASS** (27 cited entries)
- Evidence/provenance closure: **PASS** (14 source hashes, 307 rows, 67 claim
  IDs, 94 generated macros)
- Font gate: **PASS** (all embedded; no Type 3)
- PDF anonymity/metadata gate: **PASS**
- LaTeX diagnostics gate: **PASS** (no undefined references/citations or
  layout-affecting overfull boxes)

## Repository regression status

The project-mandated commands were rerun after the revision was finalized:

- `make`: **PASS**.
- `make test`: **482 passed, 2 failed, 3 warnings**. Both failures are legacy
  Gate-03 working-tree scope checks. Their first rejected path is the unrelated,
  already modified
  `campaigns/iscas_sustainability_extension/green_matrix_v3_2/CAMPAIGN_STATUS.json`;
  the validator reports 276 out-of-scope dirty paths.
- `python3 -m pytest -q`: **718 passed, 5 failed**. It includes the same two
  scope failures plus three unrelated ISCAS campaign seal/hash failures:
  Attempt-10 activity source-hash mismatch, final-artifact-manifest size
  mismatch, and frozen green-v3.2 tree drift.

None of the five failing tests reads `paper/date2027_revision/` or reports a
DATE manuscript, evidence-source, provenance, numerical, LaTeX, or PDF defect.
The pre-existing campaign files were preserved rather than deleted, reverted,
staged, or added to a legacy allowlist merely to force a green result.

## Final classification

**DATE_2027_D9_D13_SUBMISSION_READY**

The classification means that the frozen evidence, claim discipline, required
experimental breadth, and final PDF justify submission. It does not erase the
explicit single-trace limitation, guarantee reviewer agreement on novelty, or
classify the unrelated dirty ISCAS campaign tree as regression-clean.
