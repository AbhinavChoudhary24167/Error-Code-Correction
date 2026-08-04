# GREEN-ECC-PHY

GREEN-ECC-PHY is a research framework for registering error-correcting code (ECC) identities, verifying concrete encoder/decoder policies, normalizing workloads, attaching evidence-gated implementation records, and studying reliability–energy–carbon selection. It keeps mathematical codes, decoder behavior, deployment architecture, backend provenance, scenario assumptions, and result evidence separate so that a family label cannot be mistaken for a verified guarantee or a structural proxy for physical power, performance, and area (PPA).

## Evidence level and current status

<!-- BEGIN GENERATED:CURRENT_STATUS -->
**Current regenerated evidence:** 15 mathematical code specifications, 17 encoder/decoder implementations, 17 deployment architectures in the registry, and 15 selectable implementations.

The exact-functional and analytical study has 192 scenarios; 192 have a feasible winner and 0 have none. The evidence gate records 15 passing and 2 rejected implementations. Physical objectives remain null, so no physical winner, physical PPA comparison, or measured adaptive break-even is computable.

Source: [`framework_summary.json`](green_ecc_physical_simulation/multi_ecc_evaluation/framework_summary.json) and [`software_study_summary.json`](green_ecc_physical_simulation/multi_ecc_evaluation/software_study_summary.json).
<!-- END GENERATED:CURRENT_STATUS -->

The framework uses six evidence classes: `exact_functional`, `analytical_model`, `structural_tool`, `physical_characterization`, `hardware_measurement`, and `unsupported`. Current selection results reach the first three classes only. The repository does **not** support measured physical PPA, silicon reliability, radiation validation, technology independence, measured adaptive overhead, or a physical winner.

## Identity chain

```text
mathematical code specification
  -> encoder/codeword set
    -> decoder implementation/policy
      -> verified capability
        -> deployment architecture
          -> backend + PDK/library + corner
            -> workload + scenario
              -> evidence-gated result
```

This separation is central: conventional SECDED, bounded SEC-DAEC, and bounded TAEC share one `(72,64)` extended-Hamming codeword set, but their decoder policies and verified capabilities differ.

## Where it is useful

- audit a new encoder/decoder against declared error universes;
- expose silent miscorrection and preserve counterexamples;
- compare distinct codes or policies sharing one code;
- build fair equal-payload comparisons;
- study scenario-aware analytical selection and fixed-baseline regret;
- prepare a verified RTL candidate for later physical characterization;
- reproduce the current multi-ECC research artifact.

See [Use cases](docs/USE_CASES.md) for required inputs and evidence strength, and [Limitations and valid claims](docs/LIMITATIONS_AND_VALID_CLAIMS.md) before citing a result.

## Five-minute quick start

The commands below are verified repository interfaces. Python 3.10–3.12, the packages in `requirements.txt`, GNU Make, and a C++17 compiler are required for the full test suite.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python eccsim.py doctor --json
python eccsim.py ecc list
python eccsim.py ecc verify --implementation hsiao-generated-combinational-72-64-v1
```

On Bash/WSL, activate with `source .venv/bin/activate`. A warning or explicit null is expected when an optional physical tool, PDK, library, or characterized metric is unavailable.

Important commands:

```text
python eccsim.py ecc inspect --code hsiao-secded-72-64-v1
python eccsim.py ecc implementations --code extended-hamming-secded-72-64-v1
python scripts/build_multi_ecc_catalogue.py
python scripts/run_multi_ecc_framework_evaluation.py
python scripts/build_documentation.py
python scripts/build_documentation.py --check
```

## Documentation map

- [Getting started](docs/GETTING_STARTED.md) — first verified workflows.
- [Complete technical guide](GREEN_ECC_PHY_TECHNICAL_GUIDE.md) — self-contained thesis-appendix view.
- [System architecture](docs/SYSTEM_ARCHITECTURE.md) — component and evidence flows.
- [ECC catalogue](docs/ECC_CATALOGUE.md) — all current codes and implementations.
- [Verification methodology](docs/VERIFICATION_METHODOLOGY.md) — pass, partial, rejection, hashes, and counterexamples.
- [Results and interpretation](docs/RESULTS_AND_INTERPRETATION.md) — regenerated findings and figures.
- [Add a new ECC](docs/EXTENDING_WITH_A_NEW_ECC.md) — complete extension contract.
- [CLI reference](docs/CLI_REFERENCE.md) — every public command path.
- [Claim ledger](docs/CLAIM_LEDGER.md) — supported, conditional, disproved, and non-computable claims.
- [Figure index](docs/FIGURE_INDEX.md) — plots, sources, captions, and provenance.

The [documentation index](docs/index.md) provides the full reading order.

## Reproduce and validate

Rebuild the complete documentation and its current study artifacts with:

```text
python scripts/build_documentation.py
```

Then run the non-mutating staleness, link, data, hash, and CLI check:

```text
python scripts/build_documentation.py --check
```

Project validation is:

```text
make
make test
python -m pytest -q
```

No commit or push is performed by the documentation workflow.
