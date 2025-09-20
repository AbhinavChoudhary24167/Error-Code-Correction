# Literature Survey

## Error-Correcting Codes for SRAM Reliability
The foundational theory of single-error correction and double-error detection
(SEC-DED) traces back to Hamming's seminal work, which established parity-based
linear block codes for protecting stored data against independent bit flips
[1].  Subsequent textbooks provide rigorous treatments of Bose–Chaudhuri–
Hocquenghem (BCH) codes and product constructions that extend coverage to
multiple adjacent upsets while maintaining manageable decoding complexity for
on-chip memories [2].  Modern SRAM repair strategies often combine redundancy
with embedded ECC logic to tackle manufacturing defects and in-field wear-out,
highlighting the need for flexible schemes that can be tuned to device-level
failure statistics [3].

## Adaptive Protection and Cross-Layer Policies
As process variation and transient soft-error rates fluctuate over a product's
lifetime, cross-layer reliability policies adapt ECC strength and scrub
frequency to balance protection with latency and energy budgets.  Microarchitectural
proposals leverage decoder telemetry, error counters and environmental sensors
to switch between lightweight SEC-DED and stronger BCH or product codes when
fault bursts are detected [3].  Approximate storage research further explores
how applications can dynamically trade correctness for efficiency by tolerating
bounded corruption in non-critical data structures, underscoring the importance
of exposing tunable ECC knobs to system software [4].

## Sustainability and Carbon-Aware Memory Operation
Data-center scale deployments increasingly require memory subsystems to report
the environmental impact of reliability features.  Work on carbon-aware
scheduling and power provisioning shows how real-time carbon intensity signals
can steer workload placement and hardware configurations to reduce the total
footprint of computing infrastructure [5].  Integrating carbon accounting into
ECC design enables sustainability metrics such as the Environmental
Sustainability Improvement Index (ESII) that link decoder energy draw, scrub
activity and geographic carbon coefficients.  This project builds on those
insights by translating low-level gate toggles into energy and carbon estimates,
providing a reproducible path for evaluating greener reliability choices.

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
