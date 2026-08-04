# Getting started

GREEN-ECC-PHY is easiest to learn by following the evidence gates in order: inspect identities, verify behavior, regenerate the scenario study, then interpret selection. Complete setup is in [Installation](INSTALLATION.md); every command is catalogued in [CLI Reference](CLI_REFERENCE.md).

## 1. Verify the environment

From the repository root:

```text
python -m pip install -r requirements.txt
python eccsim.py doctor --json
```

These commands were verified locally. `doctor` reports Python/package/build-tool discovery and makes optional-tool absence explicit. `doctor --strict` is intended for controlled environments; a missing optional flow or a Windows runtime mismatch can cause a non-zero exit even when catalogue inspection works.

## 2. Inspect the catalogue

```text
python eccsim.py ecc list
python eccsim.py ecc inspect --code hsiao-secded-72-64-v1
python eccsim.py ecc implementations --code extended-hamming-secded-72-64-v1
```

The first command emits JSON with `code_count`, `implementation_count`, and one record per mathematical code. `inspect` exposes `(n,k)`, matrix/distance evidence, encoder identity, guaranteed correction/detection sets, source hashes, and associated implementations. `implementations` shows that the extended-Hamming codeword set has three decoder policies: SECDED, bounded SEC-DAEC, and bounded TAEC.

Important fields:

- `code_spec_id`: mathematical code/codeword-set identity;
- `encoder_id`: exact encoder identity;
- `implementation_id`: hardware/reference implementation plus decoder policy;
- `decoder_policy_id`: how syndromes become corrections, detection, or abstention;
- `manifest_sha256`, `matrix_sha256`, `source_hashes`: provenance binding;
- `verified_capabilities` and `failed_capabilities`: declared evidence scope, not a family-label promise.

## 3. Verify one passing and one rejected implementation

```text
python eccsim.py ecc verify --implementation hsiao-generated-combinational-72-64-v1
python eccsim.py ecc verify --implementation secdaec-rtl-bounded-72-64-v1
```

The Hsiao record passes 72/72 single-bit corrections and 2,556/2,556 double-bit detections in its declared universe. The bounded SEC-DAEC record is rejected because 302/2,556 double errors silently miscorrect and its adjacent-pair claim fails 53/63 patterns. The command itself exits successfully after producing a scientifically negative report; use `verification_status` and `capability_verification_status`, not process exit alone, to interpret the evidence.

See [Verification Methodology](VERIFICATION_METHODOLOGY.md) for the tested-universe hash, data-independence proof, counterexample records, and partial-verification semantics.

## 4. Regenerate the study

```text
python scripts/build_multi_ecc_catalogue.py
python scripts/run_multi_ecc_framework_evaluation.py
```

The first command validates and rebuilds `green_ecc_physical_simulation/registry/`. The second rebuilds `green_ecc_physical_simulation/multi_ecc_evaluation/`, including:

- `verification/`: one exact report per registered implementation;
- `characterization/`: evidence-gated implementation/architecture results;
- `normalized_exact_metrics.json`: rate, equal-payload, distance, and structural data;
- `exact_functional_profiles.json`: exact error-class outcomes;
- `scenario_selection_results.json`: candidate records, constraints, Pareto sets, and winners;
- `pareto_and_regret.json`: frequency and fixed-baseline regret;
- `uncertainty_and_sensitivity.json`: deterministic sensitivity cases and adaptive threshold;
- `framework_summary.json`: current evidence gates and defensible claim.

## 5. Build and read the documentation

```text
python scripts/build_documentation.py
python scripts/build_documentation.py --check
```

The build regenerates the catalogue and study, creates all figure data and formats, updates marked generated sections, validates local links/JSON/CSV/hash provenance/CLI help, and writes `figure_data/documentation_build_summary.json`. The check is non-mutating and fails on stale content.

Start interpretation with [Results and Interpretation](RESULTS_AND_INTERPRETATION.md). The essential boundary is simple: exact functional behavior and analytical scenario selection are available; physical PPA and a physical winner are not.
