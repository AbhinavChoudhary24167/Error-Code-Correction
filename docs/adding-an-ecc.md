# Adding an ECC

1. Choose a new stable code ID. Add a mathematical-code manifest under `green_ecc_physical_simulation/registry/codes/`; do not reuse an ID for changed mathematics.
2. Add a separate implementation manifest under `implementations/` describing encoder/decoder policy, limits, latency, source adapter, and hashes.
3. Add a deployment architecture under `architectures/` when placement, banking, sharing, gating, interleaving, or service policy changes.
4. Update `registry.json` additively and validate its schema and scientific-source hashes.
5. Implement the adapter in the relevant software/RTL module without changing baseline selector behavior.
6. Define the supported error universe and expected outcome semantics. Run exact verification and retain counterexamples.
7. Add deterministic unit tests, negative tests, and golden CLI coverage. New ML assistance belongs under `ml/` and cannot override the baseline selector.
8. If physical characterization is intended, start a new experiment contract; never copy evidence from another implementation merely because the family name matches.

Minimum acceptance commands:

```bash
python eccsim.py ecc list
python eccsim.py ecc verify --implementation NEW_IMPLEMENTATION_ID
make artifact-check
make test
python -m pytest -q
```

Document code rate, parity construction, declared correction/detection set, miscorrection behavior, status contract, unsupported masks, and evidence level. A mathematical claim may qualify before physical cost; keep those states separate.
