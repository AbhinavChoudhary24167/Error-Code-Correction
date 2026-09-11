# Attempt10 carbon model

The model separates embodied, operational, recovery, and total lifecycle carbon. Equations and units are machine-readable in `CARBON_ASSUMPTIONS.json`. Embodied carbon requires a SKY130-specific manufacturing intensity, yield allocation, and lifetime allocation; none is supplied. Operational carbon requires activity-qualified energy/access plus a qualified lifetime workload and grid factor. Recovery carbon requires a recovery-event model.

The repository's `carbon_calib.json` and `carbon_defaults.json` are hashed and preserved read-only. Their grid values are retained as provenance-limited sensitivity scenarios, but the nearest-node fallback is disabled because it would substitute 28 nm data for SKY130. The activity study has incomplete mapped-net coverage and no validated SRAM internal-energy characterization. Consequently embodied, operational, recovery, and total carbon remain **NOT_QUALIFIED**. `CARBON_SENSITIVITY.csv` records the full grid/workload scenario space without promoting those scenarios to claims.

No instantaneous power is multiplied by an arbitrary time. No carbon value enters normalization or selection until every computation gate is satisfied.
