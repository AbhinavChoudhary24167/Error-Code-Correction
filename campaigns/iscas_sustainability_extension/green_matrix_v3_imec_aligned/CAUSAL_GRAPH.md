# Causal graph

The machine-readable graph is `CAUSAL_GRAPH.json`.  Its principal chains are:

```text
technology -> process route -> process steps -> fab energy/process gases
fab energy + manufacturing-grid CI + process gases -> wafer carbon
die area -> gross dies and yield -> good-die carbon

ECC + interleaving -> implementation cost and physical mapping
physical mapping + fault-topology distribution -> SDC/DUE

workload + service policy + implementation -> activity -> operational energy
operational energy + use-grid CI -> operational carbon

good-die allocation + operational carbon -> lifecycle carbon
SDC/DUE + service policy -> correct-service probability -> correct services
lifecycle carbon / correct services -> CSCI
```

Patterning electricity is a diagnostic subset of Scope 2, not an extra addend.
Correction energy is either inside measured read energy or separately
incremental, never both.  Mask NRE is amortized once over production and not
multiplied into each wafer route.  Base-memory and incremental-ECC embodied
allocations are disjoint.
