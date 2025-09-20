# Simulation Framework

## 1. Architecture Overview
The simulation environment stitches together C++ microarchitectural models and
Python analysis pipelines to emulate large-scale SRAM deployments.  The
Hamming- and BCH-based binaries generate detailed correction logs, while
`scripts/` and `analysis/` notebooks aggregate results into Pareto frontiers and
sensitivity tables.  All executables share a common configuration schema that
encodes word size, scrub cadence, burst statistics and regional carbon
coefficients, ensuring that comparative studies use consistent assumptions.

## 2. Fault Injection and Workloads
Each simulator accepts stochastic seeds that drive an identical library of fault
injectors covering isolated bit flips, clustered MBUs up to length three and
random parity-bit disturbances.  Address sampling follows a sparse indirection
scheme so that billions of logical locations can be represented without
exhausting host memory.  Workloads combine steady-state background traffic with
stress phases that raise the error rate to emulate voltage droops or radiation
spikes captured in field telemetry.

## 3. Measurement Infrastructure
Instrumentation embedded in the simulators records correction outcomes, retry
counts and decoder latency.  The `telemetry.hpp` utilities emit JSON and CSV
artifacts that the Python post-processing layer converts into failure-in-time
(FIT) statistics, Environmental Sustainability Improvement Index (ESII) scores
and carbon-per-GiB estimates.  The `energy_model.py` calibration dataset maps
logic operations to dynamic energy and leakage, enabling scenario sweeps that
track both silicon area and sustainability costs.

## 4. Reproducibility Features
Containerised dependency manifests, deterministic random seeds and continuous
integration tests in `tests/` guarantee repeatable experiments.  Every dataset
stored under `reports/examples/` is generated from a documented command script,
allowing reviewers to retrace the analysis pipeline from raw bit-flip traces to
publication-quality plots.  The framework can be extended with additional codes
or device parameters by modifying JSON schemas without altering the analysis
machinery.
