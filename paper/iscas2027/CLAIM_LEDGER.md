# ISCAS 2027 Claim Ledger

This ledger was created with the evidence audit and before manuscript prose.
Numerical wording is admitted only after the source, boundary, and qualification
status are recorded in `RESULT_PROVENANCE.csv`.

## A. Proven facts

1. The named conventional SECDED and Hsiao RTLs provide a 64-bit payload in a
   72-bit codeword and implement the declared W1-correction/W2-detection service.
   The repository combines frozen exact evidence with fresh finite regressions.
2. The named BCH `(78,64,t=2)` RTL implements the declared W1/W2-correction
   service under its recorded proof/regression boundary. This is a claim about one
   RTL identity, not BCH implementations in general.
3. U0, SECDED, Hsiao, and BCH each have ten fresh routed/GDS records across two
   constraints and five deterministic route seeds; every retained final route has
   zero reported route DRC errors.
4. At 10 ns, U0 and conventional SECDED are setup- and hold-clean in 5/5 seeds;
   Hsiao is setup-clean in 5/5 and hold-clean in 4/5; BCH is setup-clean in 0/5.
5. For seeds 13, 17, 19, and 23, conventional SECDED and Hsiao form four matched
   setup-and-hold-clean pairs with all five operation classes qualified at the
   post-route ECC-logic activity boundary.
6. Each primary E5 record uses 16 warm-up cycles, 256 measured operations,
   zero-delay final-routed-netlist VCD activity, final SPEF parasitics, all 72
   required SRAM-output roots, and explicit hashes for result, activity, netlist,
   workload, and SPEF.
7. The inherited SRAM22 Liberty views do not establish complete
   address/data/state-dependent macro-internal energy. Whole-memory E5 is not
   qualified.
8. Physical bit topology, Qcrit, particle-beam event rates, absolute FIT/SDC/DUE,
   and a matched SKY130 manufacturing inventory are absent or blocked.
9. Missing quantities remain missing; the current evidence does not qualify a
   global sustainability winner.

## B. Supported interpretations

1. Reliability requirements must be applied categorically before cost
   comparison. U0 is infeasible whenever W1 correction is required, while the
   routed BCH identity is infeasible at the common 10 ns setup target despite its
   stronger declared correction service.
2. Within the four fully timing-clean matched pairs, conventional and Hsiao
   SECDED exchange physical and operation-energy advantages. Hsiao uses more
   standard-cell area, routed wire, and vias; its mean setup slack is larger.
3. Operation mix changes the lower-energy implementation within the admitted
   equal-service pair. Clean read can favor Hsiao, whereas write, single-error
   correction, and double-error detection favor conventional SECDED throughout
   the primary four-seed cohort.
4. A workload crossover can be stated as a measured-coefficient inequality.
   It is a decision boundary, not a learned workload distribution or deployed
   application claim.
5. At positive operation count and grid intensity, operational-carbon ordering
   has the same sign as operation-energy ordering. Absolute lifecycle ordering
   additionally depends on an unqualified embodied-carbon difference and can only
   be expressed as a symbolic break-even threshold.
6. The evidence-preserving join is scientifically useful because it prevents a
   stronger but timing-infeasible code, an unprotected low-cost baseline, or an
   unqualified macro-energy estimate from entering the same Pareto population as
   qualified service delivery.

## C. Hypotheses

1. Hsiao's lower clean-read switching contribution may arise from parity-matrix
   structure and routed switching distribution, but the retained data do not
   isolate logic cones or causal cell arcs.
2. A pipelined BCH implementation may meet 10 ns, but no such memory transaction
   identity is implemented or qualified in this campaign.
3. Qualified macro-internal energy could reduce, preserve, or reverse the
   ECC-logic workload boundary. Its direction is unknown.
4. A physical interleaving map could change conditional MBU service, but no
   numerical reliability benefit is presently identifiable.
5. A matched SKY130 manufacturing inventory could shift lifecycle crossovers;
   its sign and magnitude cannot be inferred from advanced-node literature.

## D. Unsupported claims that must NOT appear

- Hsiao, conventional SECDED, BCH, or U0 is globally greenest.
- Stronger ECC is always greener, or any numerical answer to "when is stronger
  ECC greener?" from the current data.
- The campaign measures whole-memory energy, SRAM macro power, silicon power,
  Fmax, or silicon reliability.
- The seed set supports p-values, confidence intervals, statistical
  significance, or population inference.
- SECDED/Hsiao categorical guarantees imply a FIT, SDC, DUE, lifetime, or field
  failure-rate improvement.
- The 256x72 OpenRAM macro is freshly generated, DRC-clean, LVS-clean,
  characterized, timing-qualified, or power-qualified.
- Inherited SRAM22 views are foundry-signoff macros or a freshly generated
  integrated SRAM+ECC system.
- Advanced-node imec or ACT coefficients are SKY130 manufacturing-carbon data.
- GREEN is imec-certified, imec-compliant, imec-validated, imec-endorsed, or a
  standard.
- The manually corrected Liberty view is an upstream or independently validated
  replacement rather than a counterfactual sensitivity model.
- Results generalize to another PDK, library, corner, target, workload, or ECC
  implementation family.
- The ISCAS novelty is that equivalent RTLs can have different physical results;
  that thesis belongs to the DATE paper.
- The ISCAS novelty is the vectorless-to-activity ordering change alone; an
  adjacent DATE draft already centers that question.

## Principal contributions admitted for Draft 1

1. An evidence-qualified decision method that joins categorical protection
   service, exact implementation identity, full timing feasibility, post-route
   activity energy, and lifecycle assumptions without repairing missing evidence.
2. A matched physical study spanning an unprotected baseline, two SECDED
   organizations, and one stronger BCH identity, with the activity comparison
   restricted to four fully timing-clean SECDED/Hsiao seed pairs and the BCH miss
   retained as a feasibility result.
3. A workload-dependent energy boundary and symbolic lifecycle-carbon
   break-even equation that state exactly which architecture preferences are
   identifiable without macro energy, physical failure rates, or a SKY130
   manufacturing-carbon calibration.

## Research questions

- **RQ1:** After correctness and full timing qualification, which physical and
  operation-energy trade-offs remain comparable across the admitted
  SRAM-protection identities?
- **RQ2:** Within the equal-service conventional/Hsiao SECDED pair, for which
  operation mixes does the lower-energy implementation change?
- **RQ3:** Which sustainability decisions survive when whole-memory energy,
  physical failure rates, and SKY130 embodied carbon remain unqualified?

