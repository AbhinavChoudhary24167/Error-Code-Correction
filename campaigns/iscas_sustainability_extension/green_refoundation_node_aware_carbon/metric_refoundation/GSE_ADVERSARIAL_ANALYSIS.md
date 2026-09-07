# GSE adversarial analysis

The adversarial suite supports retaining GSE, subject to input qualification and feasibility/Pareto policy.

- Reliability is never a free weighted bonus. Correct normal, corrected, and recovered-after-retry transactions contribute service; SDC, unrecovered DUE, and SLA failures do not.
- Extremely strong reliability can lose to a lower-carbon baseline: `0.999999/100 < 0.99/1` on a matched service basis.
- A very low-carbon design with unacceptable SDC cannot buy feasibility through a large GSE. It is excluded only by an externally justified SDC threshold; absent that threshold, SDC is a separate Pareto axis and no acceptability claim is made.
- Retry and scrubbing can improve later/useful service, but their activity energy appears once in operational carbon. They are not extra numerator credit or a second recovery-carbon charge.
- Longer lifetime increases service and operational carbon together while amortizing fixed embodied carbon. Grid decarbonization reduces only operational carbon under fixed energy, making embodied uncertainty relatively more important.
- Interleaving and stronger ECC remain genuine tradeoffs: physical topology changes Q, while routing/area/energy changes lifecycle carbon. GSE does not preordain the winner.
- At zero/near-zero fault rate, incremental Q tends to zero while ECC carbon remains; stronger protection is not automatically favored.

These are property/behavior tests, not qualified architecture results. Until activity, SRAM macro energy, physical fault mapping, and node calibration reach their evidence gates, the cases remain `PARAMETRIC_ADVERSARIAL_TEST`.
