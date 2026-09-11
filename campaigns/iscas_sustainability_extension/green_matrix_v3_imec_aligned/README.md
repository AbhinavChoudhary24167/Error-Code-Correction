# GREEN Matrix 3.0

**Evidence-Aware Reliability–Sustainability Design Space for Memory Systems**

This additive campaign supersedes GREEN Matrix v2 as the primary research
model without changing any historical artifact or default CLI behavior.  Its
central question is: given explicit reliability/service constraints, which
feasible architecture has the smallest defensible environmental burden under
declared manufacturing, operating, workload, fault, interleaving, policy, and
lifetime scenarios?

The source of truth is normalized and sparse:

- `MATRIX_P.*` contains physical/architectural observations.
- `MATRIX_E.*` contains quantity-level provenance and evidence status.
- `MATRIX_S.*` contains scenario-dependent sustainability translations.
- `GREEN_MATRIX_V3_VIEW.*` is derived and is never the sole source of truth.

The conceptual design space is `G[A,N,F,I,W,P,G,L,M]`.  Configuration files in
`config/` add architectures, nodes/routes, workloads, physical fault models,
interleavers, fab/grid scenarios, service policies, metrics, and sources without
changing the scientific equations.

Current data support exact logical-control/area diagnostics only.  Physical
fault probabilities, workload-qualified energy/latency, matched SKY130
manufacturing carbon, lifetime activity, CSCI, MRCC, and a global architecture
winner remain blocked.

Rebuild with:

```text
python campaigns/iscas_sustainability_extension/green_matrix_v3_imec_aligned/build_campaign.py
```

The classification is
`GREEN_MATRIX_V3_FOUNDATION_VALIDATED_IMEC_ALIGNED_PARTIAL_POPULATION`.
“IMEC aligned” means alignment to public methodological evidence, not imec
certification, compliance, endorsement, or a foundry-specific inventory.
