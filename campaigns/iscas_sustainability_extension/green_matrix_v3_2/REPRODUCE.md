# Reproducing GREEN Matrix v3.2

From the repository root:

```bash
python3 -m campaigns.iscas_sustainability_extension.green_matrix_v3_2.build_campaign
python3 -m pytest -q tests/test_green_matrix_v3_2_evidence_aware.py
make
make test
python3 -m pytest -q
```

To bind generated artifacts to a validated implementation commit, pass:

```bash
python3 -m campaigns.iscas_sustainability_extension.green_matrix_v3_2.build_campaign \
  --campaign-commit <40-character-commit-sha>
```

Generation reads only repository artifacts and is byte deterministic for a
fixed campaign-commit argument. No network source, random seed, physical tool,
or mutable external state is consulted. The declared scenario space is finite
and enumerated exactly; its values are assumptions, not measurements.
