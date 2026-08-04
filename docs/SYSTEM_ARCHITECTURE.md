# System architecture

The framework is a sequence of explicit evidence gates rather than one monolithic selector.

```mermaid
flowchart TD
    A["Code and implementation manifests"] --> B["Schema + hash validation"]
    B --> C["Factory-loaded normalized adapter"]
    C --> D["Exact functional verification"]
    D -->|pass/partial| E["Capability-gated catalogue"]
    D -->|fail| R["Retained rejected record"]
    E --> F["Architecture compatibility"]
    F --> G["Backend characterization"]
    G --> H["Exact / analytical / structural / physical fields"]
    H --> I["Fairness-view and scenario constraints"]
    I --> J["Pareto membership and deterministic selection"]
    J --> K["Hash-bound reports and figures"]
```

## Component map

| Component | Responsibility | Principal files |
|---|---|---|
| CLI integration | Public catalogue, verification, characterization, physical selection and legacy commands | `eccsim.py`, `green_ecc_phy/cli.py` |
| Contracts | `DecodeResult`, status semantics, adapter protocol | `green_ecc_phy/contracts.py` |
| Registry | Schema validation, identity checks, matrix resolution, factory creation | `green_ecc_phy/registry.py`, `green_ecc_phy/loading.py` |
| Adapters | Normalize linear, BCH and external encoders/decoders | `green_ecc_phy/adapters.py`, `green_ecc_phy/bch.py` |
| Verification | Enumerate declared universes, compare golden data, bind hashes/tools | `green_ecc_phy/verification.py` |
| Backends | Null-safe structural/physical result normalization | `green_ecc_phy/backends.py` |
| Comparison | Fairness views and physical-only selection | `green_ecc_phy/comparison.py` |
| Study | Exact profiles, payload normalization, analytical scenario grid, regret/stability | `green_ecc_phy/study.py` |
| Documentation figures | Independent Pareto audit, data export, SVG/PNG/PDF | `green_ecc_phy/pareto_validation.py`, `scripts/generate_documentation_figures.py` |

## Verification gate

```mermaid
flowchart TD
    A["Resolve code + implementation + sources"] --> B{"Schema and hashes valid?"}
    B -->|no| X["Reject: provenance/configuration failure"]
    B -->|yes| C["Create adapter"]
    C --> D["No-error, deterministic encode, malformed input"]
    D --> E["Enumerate each declared correction/detection universe"]
    E --> F["Harness compares decoded data with golden data"]
    F --> G{"Every guaranteed class passes?"}
    G -->|no| H["Rejected; preserve counts + counterexamples"]
    G -->|yes, implementation claim fails| I["Partially verified; failed claim excluded"]
    G -->|yes| J["Fully verified for declared universe"]
```

## Characterization eligibility

```mermaid
flowchart TD
    A["Registered implementation"] --> B{"Functional verification passed?"}
    B -->|no| R["No characterization/selection eligibility"]
    B -->|yes| C{"Architecture permits implementation?"}
    C -->|no| R2["Reject incompatible pair"]
    C -->|yes| D{"Backend available and evidence bound?"}
    D -->|structural only| S["Emit structural record; physical fields null"]
    D -->|physical context complete| P["Emit physical characterization"]
    D -->|unavailable| N["Emit explicit not-characterized record"]
```

## Deployment architectures

```mermaid
flowchart LR
    F["Fixed"] --> F1["One implementation\nno runtime transition"]
    C["Configurable gated-parallel"] --> C1["Multiple datapaths\narchitecture-owned MUX/controller"]
    A["Adaptive shared-datapath"] --> A1["Runtime policy\ntransition + re-encoding obligations"]
    W["Placement granularity"] --> W1["Whole memory"]
    W --> W2["Bank"]
    W --> W3["Page"]
```

Fixed manifests establish a deployment identity without adaptation cost. Configurable and adaptive forms explicitly own selection logic, MUX/controller cost, state transition, metadata, and possible data re-encoding. Those costs are not measured in the current artifacts; architecture feasibility is therefore unresolved rather than free.

## Evidence hierarchy

```mermaid
flowchart BT
    U["unsupported / null"] --> E["exact functional"]
    U --> A["analytical model"]
    U --> S["structural tool"]
    E --> P["physical characterization\nbackend + PDK/library + corner"]
    A --> P
    S --> P
    P --> H["hardware measurement"]
```

The arrows indicate additional prerequisites, not that analytical or structural evidence automatically becomes physical. Evidence classes remain separate fields throughout.
