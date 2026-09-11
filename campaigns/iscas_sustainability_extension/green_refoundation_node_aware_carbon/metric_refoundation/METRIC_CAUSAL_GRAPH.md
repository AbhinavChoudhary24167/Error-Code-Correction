# Metric causal graph

```mermaid
flowchart LR
  T[Process technology and route] --> PW[Wafer processing]
  T --> DENS[Density and cell architecture]
  PW --> CW[Wafer carbon]
  DENS --> AREA[Host plus ECC die area]
  AREA --> GD[Gross dies per wafer]
  AREA --> Y[Yield]
  CW --> CEMB[Embodied carbon per good die]
  GD --> CEMB
  Y --> CEMB

  ARCH[ECC architecture] --> AREA
  ARCH --> EN[Encode/decode/correction energy]
  ARCH --> LAT[Latency]
  INT[Physical interleaving] --> AREA
  INT --> EN
  INT --> LAT
  INT --> MAP[Faults per logical codeword]

  FAULT[Physical fault environment] --> MAP
  MAP --> OUT[SDC/DUE/corrected outcomes]
  SCRUB[Scrub/retry/recovery policy] --> OUT
  SCRUB --> EN
  OUT --> RETRY[Retry/recovery activity]
  RETRY --> EN
  OUT --> Q[Correct-service yield Q]
  LAT --> I[Service-policy indicator I_k]
  Q --> I

  WORK[Workload and lifetime] --> EN
  EN --> ELC[Lifetime operational energy]
  GRID[Use-phase grid CI] --> COP[Operational carbon]
  ELC --> COP

  I --> S[Useful correct payload-bit service]
  CEMB --> CLC[Lifecycle carbon]
  COP --> CLC
  REPL[Qualified replacement burden] --> CLC
  S --> GSE[GSE = S / C_LC]
  CLC --> GSE
```

Latency enters useful service only when an externally declared SLA exists. Otherwise latency remains a separate Pareto dimension. Recovery energy is part of operational energy exactly once; only distinct replacement/maintenance burdens use a separate lifecycle term.
