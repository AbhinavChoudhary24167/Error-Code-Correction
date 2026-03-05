# ML Integration Design

## Invariants

- Backward compatibility is mandatory.
- Existing command behavior is unchanged unless ML is explicitly enabled.
- Existing JSON/CSV field names for non-ML flows are unchanged.
- ML is advisory-only and never bypasses hard constraints.

## Architecture

- `ml/features.py`: canonical feature/target extraction.
- `ml/dataset.py`: artifact ingestion and dataset generation.
- `ml/train.py`: deterministic seeded training (classifier + regressors).
- `ml/predict.py`: inference, confidence scoring, OOD detection.
- `ml/model_registry.py`: model bundle persistence (`model.joblib`).
- `ml/explain.py`: compact decision explanations.

## Data Flow

1. Build dataset from ECC artifacts (`pareto.csv`, candidate CSVs, telemetry-compatible CSVs).
2. Generate:
   - `dataset.csv`
   - `dataset_schema.json`
   - `dataset_manifest.json`
3. Train ML bundle with fixed seed.
4. Emit model artifacts:
   - `model.joblib`
   - `metrics.json`
   - `features.json`
   - `thresholds.json`
   - `model_card.md`

## Decision Flow (Selector)

1. Run baseline selector and compute feasible set.
2. Enforce hard constraints first (`fit_max`, `latency_ns_max`, `carbon_kg_max`).
3. Run ML prediction only when `--ml-model` is provided.
4. If confidence is below threshold or OOD score exceeds threshold, fallback to baseline.
5. Report baseline recommendation, ML recommendation, final decision, confidence, and constraint audit.

## Safety

- OOD is based on max absolute z-score against training feature statistics.
- Confidence threshold and OOD threshold are stored in `thresholds.json`.
- Any uncertainty path is explicit and traceable in CLI output via fallback reason.
