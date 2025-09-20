# Problem Formulation

## 1. Motivation
Aggressive technology scaling and data-center consolidation magnify both the
soft-error susceptibility and the environmental cost of large SRAM arrays.  The
traditional objective of maximizing raw reliability through strong ECC must now
be reconciled with stringent power budgets and corporate carbon pledges.  Our
study therefore frames ECC selection as a multi-objective optimisation task that
captures failure-in-time (FIT) rates, latency, silicon area, dynamic energy and
associated carbon emissions.

## 2. Research Questions
1. **Reliability Envelope** – What combinations of SEC-DED, triple-adjacent
   error correction (TAEC) and BCH codes keep the expected FIT rate below
   mission-mode targets across stochastic mixtures of single-bit, multi-bit and
   burst faults?
2. **Sustainability Impact** – How does the extra logic toggle activity and
   memory scrub frequency required by stronger ECC translate into incremental
   energy draw and regional carbon footprint?
3. **Operational Policy** – When telemetry detects a rising error rate, which
   adaptive strategy (code switching, scrub acceleration or both) minimises
   carbon cost while preserving service-level agreements?

## 3. Scope and Constraints
- The simulators operate on sparse address traces that statistically represent
  capacities up to 128 Gb without the memory overhead of enumerating every cell.
- Fault injection covers independent single-bit flips, clustered multi-bit
  upsets (MBUs) and parity-bit corruptions; permanent stuck-at faults are out of
  scope for the current study.
- Energy accounting is derived from the calibrated gate models in
  `energy_model.py` and uses carbon intensity coefficients provided in the
  configuration files.  While absolute values depend on the calibration source,
  relative comparisons remain valid across technology generations.

## 4. Hypotheses
- SEC-DED with periodic scrubbing suffices for low-voltage regimes when the bit
  upset rate remains below 10⁻¹⁴ errors/bit-hour, keeping FIT below
  10⁻¹²/Gb-year without incurring large carbon penalties.
- TAEC or BCH strengthens resilience against MBUs but increases both logic area
  and decoder energy, so adaptive activation is preferable to static deployment
  in lightly stressed environments.
- Integrating carbon intensity awareness into ECC control loops reduces the
  Environmental Sustainability Improvement Index (ESII) variance across regions,
  enabling datacenter operators to meet carbon targets while maintaining memory
  availability.
