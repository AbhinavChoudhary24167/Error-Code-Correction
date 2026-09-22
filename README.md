# GREEN: evidence-aware SRAM ECC evaluation

GREEN is an evidence-aware research framework for evaluating SRAM error-correcting-code (ECC) choices across logical reliability, physical implementation, operational energy, latency, and sustainability assumptions. It separates code identity, decoder policy, physical measurements, model parameters, and decision rules so that available data cannot be mistaken for qualified evidence.

**Current boundary:** the repository reproduces exact/analytical ECC studies, a frozen 40-run matched OpenROAD/ORFS population, and 46 activity-qualified post-route **ECC-logic-only** E5 records for SECDED and Hsiao SECDED. SRAM macro-internal energy, physical event rates and FIT, SKY130 lifecycle carbon, and a global ECC winner remain unqualified.

## Start here

| Goal | Entry point |
|---|---|
| Install and run a deterministic smoke test | [Getting started](docs/getting-started.md) |
| Use the CLI and compare ECC candidates | [User guide](docs/user-guide.md) and [CLI reference](docs/CLI_REFERENCE.md) |
| Review claim boundaries and source evidence | [Reviewer guide](docs/reviewer-guide.md) and [Evidence map](docs/evidence-map.md) |
| Reproduce a software study or audit a campaign | [Reproducibility](docs/REPRODUCIBILITY.md) |
| Add an ECC implementation or experiment | [Developer guide](docs/developer-guide.md) |

## Repository status

| Component | Status | Evidence boundary |
|---|---|---|
| ECC registry and declared decoder behavior | Validated within declared universes | 15 code specifications and 17 implementations; rejected implementations remain visible |
| Conditional logical reliability | Validated/analytical | Exact outcome fractions under declared logical mask classes; not physical event rates |
| Matched physical population | Partial | 40 inherited SKY130HD/SRAM22 OpenROAD runs; timing failures are retained |
| Activity-aware energy | Partial | 46 E5 ECC-logic records for 10 ns SECDED/Hsiao runs; whole-memory E5 is blocked |
| Fresh OpenRAM 256×72 macro | Blocked | Generation timed out after 10,800 s; DRC, LVS, and characterization did not complete |
| Physical SDC/DUE/SER/FIT and Qcrit | Blocked | Physical event distribution and verified bitcell-to-logical mapping are missing |
| SKY130 manufacturing/lifecycle carbon | Blocked | No qualified node-native inventory/yield/lifetime population |
| Global ECC ranking | Not qualified | `NO_GLOBAL_WINNER_QUALIFIED` |

## Registry-study generated snapshot

The block below is regenerated from the reusable registry study. It describes that software study's evidence ceiling; the additive campaign status above remains authoritative for later E4/E5 evidence.

<!-- BEGIN GENERATED:CURRENT_STATUS -->
**Current regenerated evidence:** 15 mathematical code specifications, 17 encoder/decoder implementations, 17 deployment architectures in the registry, and 15 selectable implementations.

The exact-functional and analytical study has 192 scenarios; 192 have a feasible winner and 0 have none. The evidence gate records 15 passing and 2 rejected implementations. Physical objectives remain null, so no physical winner, physical PPA comparison, or measured adaptive break-even is computable.

Source: [`framework_summary.json`](green_ecc_physical_simulation/multi_ecc_evaluation/framework_summary.json) and [`software_study_summary.json`](green_ecc_physical_simulation/multi_ecc_evaluation/software_study_summary.json).
<!-- END GENERATED:CURRENT_STATUS -->

## Research question

How should SRAM ECC architectures be evaluated and selected when reliability, physical implementation cost, operational energy, latency, and lifecycle/sustainability considerations must be considered jointly rather than independently?

The implemented method is narrower than this question: it can qualify some layers and stop at missing evidence. It does not yet support an absolute, all-layer ranking.

```text
Research question
  -> evaluation methodology
  -> evidence model
  -> implementation
  -> experiments
  -> qualified conclusions (or an explicit blocker)
```

## Key capabilities

- versioned mathematical-code, implementation, deployment, backend, workload, and scenario registries;
- exact functional verification with retained counterexamples;
- seeded SRAM simulation and analytical reliability/energy/carbon models;
- fair, null-safe Pareto and selection analysis;
- matched OpenROAD/ORFS physical evidence with seed, clock, PDK, tool, and hash provenance;
- activity-qualified ECC-logic power/energy records with explicit coverage;
- advisory-only ML with deterministic fallback;
- deterministic artifact and documentation checks.

## Quick start

Python 3.10–3.12 is the recorded portable range. From the repository root:

```bash
python -m venv .venv
# Bash/WSL: source .venv/bin/activate
# PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
make reviewer-smoke
```

`reviewer-smoke` validates the canonical artifact, checks documentation links, verifies one registered Hsiao implementation, runs a small seeded SRAM simulation, and executes representative tests. It does not run OpenROAD or OpenRAM and does not modify a frozen campaign.

To inspect the registry directly:

```bash
python eccsim.py ecc list
python eccsim.py ecc verify --implementation hsiao-generated-combinational-72-64-v1
```

## Supported ECC architectures

The primary matched campaign includes U0, conventional SECDED, Hsiao SECDED, and shortened BCH(78,64,t=2). SEC-DAEC was excluded after a preserved functional counterexample. The general registry contains additional archived/synthesized codes and implementations. See [ECC architectures](docs/ecc-architectures.md) and the generated [ECC catalogue](docs/ECC_CATALOGUE.md).

## Methodology overview

GREEN evaluates evidence in causal order:

```text
fault assumptions -> logical corruption -> ECC response -> service outcome
  -> implementation cost and energy -> lifecycle translation -> decision policy
```

Each transition is gated. Missing physical event probabilities, macro power, or manufacturing inventory remains missing; it is never replaced with zero or promoted by downstream arithmetic. See [Methodology](docs/methodology.md), [Evidence model](docs/evidence-model.md), and [Matrix and optimization](docs/matrix-optimization.md).

## Repository structure

| Path | Purpose |
|---|---|
| `eccsim.py` | Public CLI; legacy interfaces are preserved |
| `green_ecc_phy/` | Registry, adapters, verification, physical normalization, and comparison |
| `architecture/` | Deployment, scheduling, transition, and DSE models |
| `ml/` | Advisory-only ML pipeline |
| `rtl/`, `asic/` | RTL implementations, wrappers, and testbenches |
| `campaigns/` | Immutable or additive experiment evidence and manifests |
| `configs/`, `schemas/` | User configurations and machine-readable contracts |
| `scripts/` | Reproduction, validation, and artifact tooling |
| `tests/` | Python, C++, RTL, golden, and campaign integrity tests |
| `docs/` | Public guides, generated references, and evidence interpretation |
| `reports/`, `results/` | Derived study outputs with their available provenance |

Publication manuscripts and submission PDFs are intentionally not distributed in this source repository. Reusable data, experiment code, campaign manifests, and evidence summaries remain available and are linked through the [evidence map](docs/evidence-map.md).

## Reproducing experiments

- Smoke test: `make reviewer-smoke`
- Full software validation: `make`, `make test`, then `python -m pytest -q`
- Core registry/documentation regeneration: `make reproduce`
- Physical campaign: environment-specific and expensive; follow [Physical design](docs/physical-design.md) and the frozen campaign README. The completed v3.3 queue must not be restarted as a new campaign.

See [Reproducibility](docs/REPRODUCIBILITY.md) for the three supported levels and [Reviewer guide](docs/reviewer-guide.md) for a 10–20 minute path.

## Evidence and qualification

Evidence tiers E0–E7 describe provenance strength, but qualification is metric-specific. E5 logic power does not qualify SRAM macro energy, physical FIT, or lifecycle carbon. `available data != qualified evidence`. Historical negative and partial results are part of the artifact and remain visible.

## Sustainability methodology

Operational carbon is a modelled translation of qualified energy and an explicit use-grid intensity. Manufacturing and lifecycle models keep scope, yield, grid, lifetime, and allocation assumptions separate. Current SKY130 lifecycle quantities are blocked. The method is informed by public semiconductor-sustainability literature and imec methodology; it is not imec certification, endorsement, compliance, or an independently verified lifecycle assessment.

## Physical-design and reliability flows

The retained physical evidence uses matched OpenROAD-flow-scripts/SKY130HD conditions, inherited SRAM22 macros, 10 ns and 5 ns targets, and seeds 11, 13, 17, 19, and 23. RTL-to-GDS completion, timing feasibility, DRC/LVS, and signoff are reported as distinct states. See [Physical design](docs/physical-design.md) and [Reliability model](docs/reliability-model.md).

## Known limitations

There is no silicon or radiation measurement, fresh qualified OpenRAM macro, verified physical fault topology, complete SRAM power model, SKY130-native lifecycle inventory, or globally qualified winner. See [Limitations](docs/limitations.md).

## Documentation

Start at the [documentation index](docs/README.md). New users should read [Getting started](docs/getting-started.md); reviewers should use the [Reviewer guide](docs/reviewer-guide.md); contributors should use the [Developer guide](docs/developer-guide.md) and [Contributing](CONTRIBUTING.md).

## Citation, contributing, and license

Repository citation metadata is in [CITATION.cff](CITATION.cff). No publication DOI is asserted. Cite the repository commit and relevant campaign identifier used for a result. Contributions must preserve experiment provenance and claim boundaries; see [CONTRIBUTING.md](CONTRIBUTING.md). The repository is distributed under the [MIT License](LICENSE).
