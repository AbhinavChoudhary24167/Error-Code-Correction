# Sustainability-Aware Error Correction for SRAM Systems

**Authors:** Error-Code-Correction Research Collective

## Abstract
Emerging cloud and edge workloads demand memory subsystems that simultaneously
deliver high reliability and meet aggressive sustainability targets.  This paper
presents an end-to-end evaluation framework for selecting error-correcting codes
(ECC) that satisfy failure-in-time (FIT) constraints while minimising silicon
area, latency and carbon footprint.  C++ microarchitectural simulators inject
stochastic fault patterns into 1 Gb and 128 Gb SRAM models, and Python analytics
translate correction telemetry into Environmental Sustainability Improvement
Index (ESII) and carbon-per-GiB metrics.  Across voltage sweeps and burst fault
profiles, lightweight single-error correction with double-error detection
(SEC-DED) meets datacenter FIT requirements with up to 6.17 kg CO₂ per GiB of
annual decoder energy.  Larger arrays require adaptive scrub policies to cap the
687.99 kg CO₂ per GiB attributable to background maintenance.  The integrated
workflow offers reproducible guidance for deploying greener ECC policies in
future memory platforms.

**Index Terms—** SRAM, error-correcting codes, sustainability, carbon-aware
computing, reliability modelling.

## I. Introduction
Memory corruption jeopardises availability for latency-sensitive services.  While
strong ECC traditionally prioritises reliability, the associated energy overhead
now materially influences fleet-level carbon emissions.  We investigate how ECC
choices affect both correctness and sustainability for standalone SRAMs.  Our
contributions are threefold: 1) a unified methodology that couples microarchitectural
fault injection with energy and carbon accounting; 2) quantified trade-offs
between SEC-DED, triple-adjacent error correction (TAEC) and BCH-based schemes
across representative capacities; and 3) open-source artifacts that allow peers
to reproduce every figure and extend the design space analysis.

## II. Background and Related Work
Hamming's foundational SEC-DED codes remain the baseline for SRAM protection [1],
while modern references detail BCH extensions that improve multi-bit resilience
at manageable complexity [2].  Hybrid redundancy/ECC repair flows have proven
effective for manufacturing defect screening and in-field reconfiguration [3].
Cross-layer policies increasingly employ runtime telemetry to adapt ECC strength
and scrub frequency, enabling systems to respond to transient radiation or
voltage excursions [3], [4].  In parallel, carbon-aware scheduling frameworks
inform infrastructure decisions with real-time carbon intensity signals [5].
Our study operationalises these insights by mapping ECC behaviour to energy and
emissions outcomes using the open datasets published with this work [6].

## III. Framework Overview
Fig. 1 (conceptual) illustrates the toolchain.  Parameterised C++ models for
`Hamming32bit1Gb`, `Hamming64bit128Gb` and `BCHvsHamming` emulate read/write
streams with configurable burst fault rates.  The simulators emit structured
telemetry through `telemetry.hpp`, which is post-processed by Python utilities in
`analysis/` and `scripts/`.  Energy calculations rely on `energy_model.py` to
convert gate toggles into joules, and `carbon.py` applies regional carbon
coefficients.  Resulting artifacts—Pareto fronts, sensitivity analyses and trade-off
slopes—are saved under `reports/examples/` for traceability.

## IV. Experimental Setup
Two representative scenarios demonstrate the workflow:

1. **1 Gb SRAM (32-bit words):** We model a light multi-bit upset regime with
   carbon intensity 0.55 kg CO₂/kWh and a 5 s scrub interval.  Candidate ECC
   options include SEC-DED-64, SEC-DAEC-64 and TAEC-64.
2. **128 Gb SRAM (64-bit words):** A scaled deployment with identical carbon
   intensity and scrub policy but higher background load to emulate datacenter
   caching tiers.

Random seeds, voltage grids and configuration files are bundled in the
repository to ensure deterministic regeneration of the results in
`reports/examples/` [6].

## V. Results
Table I summarises the dominant Pareto points for each scenario.  SEC-DED remains
the preferred choice across the evaluated voltage range because it satisfies the
FIT targets while minimising decoder latency.

| Scenario | FIT (failures/Gb-year) | Carbon (kg CO₂/GiB-year) | ESII | Decoder Latency (ns) |
| --- | --- | --- | --- | --- |
| 1 Gb SEC-DED-64 | 4.97×10⁻¹⁹ | 6.17 | 0.57 | 1.0 |
| 128 Gb SEC-DED-64 | 6.37×10⁻¹⁷ | 687.99 | 0.65 | 1.0 |

**A. Reliability:** The SEC-DED configuration keeps the FIT below
10⁻¹⁵ failures/Gb-year even under burst-prone conditions, validating the
hypothesis that lightweight codes suffice for low-voltage operation.

**B. Sustainability:** Background scrub energy dominates the carbon budget for
large arrays.  The trade-off analysis indicates a slope of −21.24 kg CO₂ per
order-of-magnitude FIT improvement in the 128 Gb case, motivating adaptive scrub
intervals when the observed error rate is low.

**C. Sensitivity:** Voltage sweeps from 0.7 V to 0.9 V do not change the optimal
code selection because all candidates remain feasible; however, the robustness
metric confirms that SEC-DED maintains the highest ESII across the grid.

## VI. Discussion
The results highlight how sustainability metrics can steer ECC policy.  While
TAEC and BCH offer stronger coverage, their additional logic toggles and wider
parity fields raise both silicon area and energy.  By integrating carbon
coefficients into the selection workflow, operators can defer switching to
heavier codes until telemetry reports a sustained FIT increase, reducing the
steady-state footprint without sacrificing availability.

## VII. Conclusion
We presented an IEEE-style evaluation of sustainability-aware ECC choices for
SRAM memories.  The open-source framework links microarchitectural fault models
to carbon outcomes, enabling reproducible and transparent design exploration.
Future work will expand the dataset with adaptive policies and real workload
traces to further validate the methodology.

## Acknowledgment
We thank the Error-Code-Correction community for maintaining the calibration
data and automation scripts that underpin this analysis.

## References
[1] R. W. Hamming, "Error detecting and error correcting codes," *Bell System
Technical Journal*, vol. 29, no. 2, pp. 147–160, Apr. 1950.

[2] S. Lin and D. J. Costello, *Error Control Coding*, 2nd ed. Upper Saddle
River, NJ, USA: Prentice Hall, 2004.

[3] A. DeOrio, A. Bais, M. Alam, and V. Bertacco, "A reliable SRAM repair
technique employing fused ECC and redundancy," in *Proc. Design, Automation and
Test in Europe (DATE)*, Mar. 2012, pp. 1483–1488.

[4] J. Sampson, L. Ceze, S. Swanson, and M. Taylor, "Approximate storage in
solid-state memories," *IEEE Micro*, vol. 33, no. 4, pp. 24–31, Jul.–Aug. 2013.

[5] I. Goiri, K. Le, M. E. Haque, R. Beauchea, T. D. Nguyen, J. Guitart, J.
Torres, and R. Bianchini, "Greenslot: Scheduling energy consumption in green
datacenters," in *Proc. Int. Conf. High Performance Computing, Networking,
Storage and Analysis (SC)*, Nov. 2011, pp. 1–11.

[6] Error-Code-Correction Research Collective, "Error-Code-Correction Framework
Artifacts," GitHub repository, 2024. [Online]. Available: https://github.com/
Error-Code-Correction
