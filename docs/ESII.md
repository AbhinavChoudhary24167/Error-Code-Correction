# Environmental Sustainability Improvement Index

The ESII metric quantifies the reliability gain of an ECC technique relative to
its carbon cost.  It is defined as the difference in FIT rates between the base
system and the ECC-protected system divided by the total kilograms of CO₂e
attributable to the technique.

```python
from esii import ESIIInputs, compute_esii, embodied_from_wire_area
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

`eccsim.py` exposes an ``esii`` subcommand that ties together reliability,
energy and area reports.  Provide the JSON files produced by the respective
modules along with the grid carbon intensity and output location:

```bash
python eccsim.py esii \
  --reliability reports/reliability.json \
  --energy reports/energy.json \
  --area reports/area.json \
  --ci 0.55 --embodied-override-kg none --basis per_gib \
  --out reports/esii.json
```

The tool writes a JSON object with provenance information, the inputs used, a
carbon breakdown and the resulting ESII.  Direct numeric inputs are also
accepted for quick experiments:

```bash
python eccsim.py esii --fit-base 300 --fit-ecc 5 \
  --e-dyn-j 2.1e3 --e-leak-j 1.4e3 --ci 0.55 --embodied-kg 0.05 \
  --basis per_gib --out esii.json
```

The computation can also be performed programmatically:

```python
embodied = embodied_from_wire_area(5.0, 2.0)
inp = ESIIInputs(
    fit_base=1000,
    fit_ecc=100,
    e_dyn=1.0,
    e_leak=0.5,
    ci_kg_per_kwh=0.2,
    embodied_kg=embodied,
    energy_units="kWh",
)
result = compute_esii(inp)
print(result["ESII"])
```
