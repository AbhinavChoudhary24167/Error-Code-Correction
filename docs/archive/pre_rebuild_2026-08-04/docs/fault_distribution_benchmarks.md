# Open modeled SRAM fault-distribution benchmarks

The files under `configs/fault_distributions/benchmarks/` are deterministic,
finite, conditional-on-error PMFs for algorithm evaluation. Every file records
its generator family, parameters, seed, supported width, normalization result,
and `synthetic` provenance. None is a silicon measurement.

The suite covers uniform single-bit errors, adjacent double- and triple-bit
upsets, variable bursts, non-adjacent MBUs, mixed multiplicities, spatial hot
spots, bit-position asymmetry, voltage- and temperature-sensitive mixtures,
geometry filtering, and a distribution-shift stress case.

Generate the canonical 72-bit suite with:

```text
python3 scripts/generate_fault_benchmarks.py
```

The PMFs are deliberately transparent rather than calibrated. Replacing them
with measured or fitted distributions requires changing `provenance.kind`,
recording a primary data source and derivation, and retaining the normalization
check. Results derived from the bundled suite must be described as synthetic.

The error universe is finite and explicit. Probabilities such as SDC and DUE are
therefore conditional on that universe; unlisted patterns are not implicitly
safe.
