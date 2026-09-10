# Independent internal review

Review date: 2026-09-10

Three independent, read-only passes were run on the manuscript and its evidence
package before final validation.

| Reviewer | Perspective | Initial verdict | Principal risk |
|---|---|---|---|
| A | DATE D9 design methodologies | Weak accept, 6/10 | The conjunction could look like careful hygiene unless expressed as an operational, fail-closed method. |
| B | D13/system-facing stress test | Weak reject for system-level framing; weak accept for D9 | The codec-only trace does not establish memory-subsystem or embedded-system energy. |
| C | ECC and formal methods | Conditional pass; no P0 flaw | Proof boundaries and provenance wording needed exact correction. |

The official DATE 2027 topic list was checked after Reviewer B identified a
labeling ambiguity. D9 is “Low-power, energy-efficient and thermal-aware
design”; D13 is “Physical analysis and design”; system-level design is D1.
Accordingly, D9 remains primary. D13 is a defensible but weaker secondary fit
because routed physical qualification is central, although the paper does not
claim a placement/routing algorithm.

## Attack resolution

| Priority | Attack | Disposition |
|---|---|---|
| P0 | Fig. 3 compared percentages with different denominators while making an additive component argument. | **Fixed.** Panel (a) now plots paired absolute mW differences. Top-level components and cell groups each reconcile independently to the same total; the CSV retains both percent and mW fields. |
| P0 | The method could be read as a loose conjunction of existing tools. | **Fixed.** The contribution is now an explicit fail-closed, machine-auditable admissibility protocol with named joins and rejection conditions. |
| P1 | Hsiao temporal induction was described as holding from arbitrary equal initialization. | **Fixed.** The paper and claim ledger now state the specified all-zero initialization and arbitrary reset/valid/payload/received-word sequences. |
| P1 | SECDED exact-equivalence provenance pointed only to a physical-effects summary. | **Fixed.** The Gate-03R contract, proof summary, encoder matrix, and decoder matrix are hash-registered; dedicated SECDED formal/alignment rows were added to `RESULT_PROVENANCE.csv`. |
| P1 | The trace could be challenged for unequal work or incomplete pipeline drain. | **Fixed.** The paper now names SplitMix64 and its seed, identical trace reuse, six reset cycles, 100,000 valid operations, four drain cycles, saturated II=1, overhead treatment, and excluded idle/bursty/correction-heavy scope. |
| P1 | The Introduction implied that any ECC family name fixes a codeword mapping. | **Fixed.** It now distinguishes a fully specified code identity from a family-level guarantee label. |
| P1 | Energy ineligibility incorrectly referred to the timing equation. | **Fixed.** The gate is now stated directly as a frozen-contract rule. |
| P1 | Table II mixed paired effects with absolute BCH entries. | **Fixed.** The caption distinguishes exact-equivalence effects from BCH absolute means. |
| P1 | Common utilization could be mistaken for a common die outline. | **Fixed.** The method explicitly calls timing and wire results floorplan-policy-conditioned. |
| P1 | Component wording invited a glitch-causality inference. | **Fixed.** The manuscript says the aggregate reports cannot distinguish glitch suppression from activity, capacitance, buffering, or placement changes. |
| P2 | Table and figure text was smaller than the declared 10-point policy. | **Fixed.** Both tables now use normal document text; generated plots use print-scale labels and were visually rechecked. |
| P2 | “Stable” or “survives” could overstate two constraints and five deterministic seeds. | **Fixed.** The paper uses consistent/persist language and retains explicit non-population limitations. |

## Remaining reviewer vulnerabilities

1. Novelty remains the strongest risk: a skeptical reviewer may still classify
   the admissibility protocol as unusually rigorous experimental practice rather
   than a new design methodology.
2. The -23.4% headline is a post-route OpenSTA estimate for one saturated,
   primary-input-only, no-error trace. It is not silicon, macro, burst/idle, or
   correction-heavy energy.
3. `f_slack` is a deterministic signed-slack-derived metric rather than a
   characterized maximum frequency. The paper consistently labels it and
   separately gates target feasibility.
4. D13 is secondary only: physical analysis is essential evidence, but the paper
   contributes no new physical-design engine.

## Consolidated verdict

All P0 and correctness-related P1 findings were resolved without inventing
evidence or deleting an inconvenient result. Reviewer C's final technical
assessment is a conditional pass; Reviewer A's D9 assessment improves to a
firmer weak accept after the listed changes. The remaining risks concern
reviewer valuation and scope breadth, not an unqualified claim or missing
required experiment.
