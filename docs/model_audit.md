# Pre-revision model and artifact audit

## Current data flow

The legacy path starts with CLI/scenario inputs in `eccsim.py` or
`integrated_toolkit.py`. `ecc_selector.select` resolves Qcrit and technology
calibration, computes Hazucha-style SER and MBU severity, applies ECC coverage
to obtain FIT, adds scrub energy and projected candidate area/latency, derives
legacy embodied/operational carbon, computes ESII/NESII/GREEN Score, performs
deterministic non-dominated sorting, and returns a recommendation and optional
CSV/JSON artifacts.

The architecture-aware path parses a schema-validated scenario and concrete
ECC configurations, invokes the legacy calculations through a labeled provider,
constructs fixed-container/MUX/metadata/controller/reconfiguration terms,
applies hard constraints and exact Pareto enumeration, evaluates baselines and
fixed-seed uncertainty, then emits a deployable policy plus provenance.

## Hard-coded or weakly supported assumptions found

| Location | Assumption found | Revision treatment |
|---|---|---|
| `ecc_selector.py`, candidate metric construction | Candidate logic area and latency constants are explicitly approximate | Preserved for compatibility and labeled `projected` |
| `ecc_selector.py`, metric calculation | Missing Qcrit falls back to `0.3`; charge scale `Qs=0.05`; MBU severity maps light/moderate/heavy to fixed values | Documented as legacy analytical assumptions; not recast as measurement |
| `ecc_selector.py` | Dynamic and leakage energy are zero in this path; scrub is the only populated energy term | Architecture physical-energy result remains `null` unless characterized |
| `integrated_toolkit.py` | Defaults include `0.08 um2` bitcell area, 10 s scrub, and 8760 h lifetime | New scenario schema requires explicit inputs |
| `carbon_defaults.json` | Source is labeled `placeholder` | Not accepted as evidence for characterized adaptive embodied carbon |
| `carbon_calib.json` | Node manufacturing intensities are projected defaults without foundry artifacts in this checkout | Exposed, labeled projected, and excluded from new incremental carbon unless supplied |
| `data/qcrit_sram6t.json` | Contains `example.org`, “Your Lab / University,” and an internal-run description | Treated as unverified example data; no 14 nm/PVT validation claim |
| `ecc_selector._nsga2_sort` | Deterministic non-dominated sorting with population/generation metadata, not an evolutionary loop | Exact enumeration is the new default; tractable agreement is tested |
| `esii.py` / `scores.py` | NESII is a monotone winsorized normalization of ESII; GS is a distinct utility including latency | Scores retained as diagnostic ablations, not independent validation |
| `ecc_mux.py` / `mux_model.py` | Illustrative MUX constants have no Liberty/synthesis provenance | New model uses exact logical counts and only accepts exact-PVT physical records |

## Artifact search result

No manuscript/thesis `.tex` or `.bib` entry point and no existing compiled
paper PDF were found in the repository or its enclosing ECC workspace. No
Liberty library, SDC/SPEF, SPICE deck, commercial synthesis/STA report, or
measured MUX PVT dataset was found. Existing SystemVerilog codec sources and
testbenches were found under `asic/`; the revision adds a selection MUX,
protected mode controller, and testbench there.

## Consequences for claims

- “14 nm hardware result,” “measured,” and “synthesized” are unsupported here.
- The node/VDD/temperature values in the example are scenario coordinates, not
  proof of an implementation at that PVT.
- Exact logical MUX counts, storage padding, protected metadata bits, fault-tree
  composition, Pareto membership, baseline selection, and deterministic Monte
  Carlo results are reproducible.
- Physical adaptive area, delay, energy, leakage, and incremental embodied
  carbon remain unavailable until a characterized provider is supplied.
- The original “189 scenarios” construction could not be located. The revision
  reports its actual three scenarios, five families/configurations, and fifteen
  candidate-scenario evaluations without conflating these counts.

