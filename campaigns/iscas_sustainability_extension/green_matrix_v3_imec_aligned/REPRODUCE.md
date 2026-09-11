# Reproduction

From the repository root:

```text
python campaigns/iscas_sustainability_extension/green_matrix_v3_imec_aligned/build_campaign.py
python -m pytest -q tests/test_green_matrix_v3_core.py tests/test_green_matrix_v3_artifacts.py
make
make test
python3 -m pytest -q
python campaigns/iscas_sustainability_extension/green_matrix_v3_imec_aligned/build_campaign.py --hash-only
```

The generator records the starting commit, immutable v2 Git tree, input hashes,
schema/model version, source versions, and fixed generation date.  Logical
enumeration and matrix generation are deterministic.  Seeded uncertainty uses
explicit seeds.  `FINAL_ARTIFACT_HASHES.json` covers every campaign file except
itself and interpreter caches; any stale or edited derived artifact changes the
manifest check.

Do not run the generator inside the historical v2 directory.  It reads v2 as
immutable seed provenance and writes only here.
