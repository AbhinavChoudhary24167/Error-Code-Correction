# Environmental Sustainability Improvement Index

The ESII metric quantifies the reliability gain of an ECC technique relative to
its carbon cost.  It is defined as the difference in FIT rates between the base
system and the ECC-protected system divided by the total kilograms of CO₂e
attributable to the technique.

```python
from esii import compute_esii, embodied_from_wire_area
```

## Embodied carbon from wiring

Many ECC schemes add routing resources.  The helper
`embodied_from_wire_area(area_mm2, factor_kg_per_mm2)` converts the additional
wire area into an embodied-carbon term in kilograms of CO₂e.  Multiply the
extra square millimetres of metal by a technology-dependent conversion factor
obtained from life‑cycle analyses or foundry data.

```python
embodied = embodied_from_wire_area(5.0, 0.8)  # -> 4.0 kgCO2e
```

Choose a conversion factor that reflects your process node and metal stack.  If
no data is available, start with an estimate from published manufacturing
studies and document the source when reporting results.

## Reporting ESII

`eccsim.py` can report the ESII and a breakdown of the carbon terms.  Provide
dynamic energy, leakage energy, and either an explicit embodied-carbon value or
wire area plus a conversion factor:

```bash
python eccsim.py esii --fit-base 1000 --fit-ecc 100 --E-dyn 1 --E-leak 0.5 \
  --ci 0.2 --wire-area-mm2 5 --wire-factor-kg-per-mm2 2
```

The output lists the contributions from dynamic energy, leakage energy and the
embodied component.  Include all three when quoting ESII so comparisons between
ECC schemes capture both operational and embodied impacts.
