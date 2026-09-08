# SKY130 carbon and technology translation

Official PDK documentation establishes that SKY130 is a mature 180 nm-130 nm
hybrid technology with five metal levels and a public process-mask inventory.
It does not publish a matched wafer energy, process-gas, abatement, yield, or
kgCO2e/wafer inventory. The open PDK is also labeled an experimental preview.

Consequently, the current layouts remain `MEASURED_SKY130_PHYSICAL` where the
underlying physical artifact supports that label, but SKY130 manufacturing
carbon is `BOUND_ONLY` or `PARAMETRIC_EXTRAPOLATION`. Imec N28-A14 values are
advanced-node calibration/validation evidence and are never presented as a
SKY130 coefficient. The mask list establishes route complexity, not mask-set
manufacturing carbon. No exact SKY130 wafer or die carbon is emitted.
