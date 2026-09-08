# Reproduction

From the repository root, rebuild the v3.1 adapter artifacts with:

```text
python3 -m campaigns.iscas_sustainability_extension.green_matrix_v3_physical_population.build_campaign
```

The command reads the frozen v3, Attempt09, and Attempt10 artifacts.  It does
not rerun synthesis, place-and-route, SPICE, or radiation experiments.

Validate the repository with:

```text
make
make test
python3 -m pytest -q
```
