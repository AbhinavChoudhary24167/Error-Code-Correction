# ML Scope Expansion: Concrete Implementation Plan

## Goals and Non-Goals

### Goals
- Expand ML from single-policy advice to multi-policy, uncertainty-aware advisory recommendations.
- Keep baseline selector as authoritative default and preserve existing behavior when ML flags are not used.
- Add deterministic, reproducible training/evaluation workflows with explicit artifacts.

### Non-Goals
- No default CLI output changes for non-ML flows.
- No renaming/removal of existing JSON/CSV fields.
- No bypassing hard constraints via ML.

---

## Phase Plan (4 incremental PRs)

## Phase 1: Policy-aware training/evaluation (additive)

### New CLI Flags / Commands

#### `eccsim.py ml build-dataset`
- `--label-policy {carbon_min,fit_min,energy_min,utility_balanced}` (default: `carbon_min`)
- `--utility-alpha-fit <float>` (default: `1.0`)
- `--utility-beta-carbon <float>` (default: `1.0`)
- `--utility-gamma-energy <float>` (default: `1.0`)
- `--split-strategy {random,scenario_hash}` (default: `scenario_hash`)

#### `eccsim.py ml train`
- `--model-type {rf,gbdt,linear}` (default: `rf`)
- `--calibrate-confidence {none,isotonic,platt}` (default: `none`)
- `--confidence-target-metric {accuracy,f1_macro}` (default: `accuracy`)

#### New command: `eccsim.py ml evaluate`
- Required: `--dataset <dataset_dir> --model <model_dir> --out <eval_dir>`
- Optional: `--policy <label-policy>` (default: read from dataset manifest)
- Optional: `--ood-threshold <float>` (default: read from thresholds)
- Optional: `--json`

### ML Artifact Schema Additions

#### `dataset_manifest.json` (new keys)
- `label_policy: string`
- `utility_weights: {alpha_fit: float, beta_carbon: float, gamma_energy: float}`
- `split_strategy: string`
- `feature_version: int`

#### `metrics.json` (new top-level sections)
- `classifier: {accuracy: float, f1_macro: float, top2_accuracy: float}`
- `regression: {fit: {...}, carbon: {...}, energy: {...}}` (existing keys retained)
- `policy_eval: {policy: string, policy_match_rate: float}`

#### New file: `evaluation.json`
- `summary: {rows: int, policy: string, fallback_rate: float, ood_rate: float}`
- `classification: {accuracy: float, f1_macro: float, confusion_matrix: object}`
- `regression: {fit_mae: float, carbon_mae: float, energy_mae: float}`
- `fallback_breakdown: {ood: int, low_confidence: int, constraints: int}`

---

## Phase 2: Uncertainty + OOD improvements (still advisory-only)

### New CLI Flags

#### `eccsim.py ml train`
- `--ood-method {zscore,mahalanobis,iforest}` (default: `zscore`)
- `--ood-quantile <float>` (default: `0.995`)
- `--conformal-alpha <float>` (default: `0.1`)

#### `ecc_selector.py`
- `--ml-confidence-min <float>` (optional override; defaults to model thresholds)
- `--ml-ood-max <float>` (optional override; defaults to model thresholds)
- `--ml-policy {carbon_min,fit_min,energy_min,utility_balanced}` (default: model policy)
- `--ml-debug` (emit detailed ML diagnostics in JSON only)

### ML Artifact Schema Additions

#### `thresholds.json` (new keys, existing keys retained)
- `confidence_min: float` (existing)
- `ood_max_abs_z: float` (existing)
- `ood_method: string`
- `ood_threshold: float`
- `conformal_alpha: float`
- `prediction_set_min_coverage: float`

#### New file: `uncertainty.json`
- `calibration_method: string`
- `ece: float`
- `brier_score: float`
- `coverage_at_confidence_min: float`

---

## Phase 3: Feature enrichment from existing artifacts

### New CLI Flags

#### `eccsim.py ml build-dataset`
- `--feature-pack {core,core+telemetry,core+telemetry+workload}` (default: `core`)
- `--enable-feature <name>` (repeatable; additive opt-in)
- `--disable-feature <name>` (repeatable; additive opt-out)

### Dataset Schema Additions
- Keep existing columns unchanged.
- Add optional columns (when feature pack enables them), e.g.:
  - `mbu_class_idx`
  - `scrub_log10_s`
  - `fit_per_watt_proxy`
  - `ser_slope_vdd`
  - `telemetry_retry_rate`
- `dataset_schema.json` to include:
  - `feature_pack: string`
  - `enabled_features: [string]`
  - `disabled_features: [string]`

---

## Phase 4: Lifecycle operations and drift checks

### New CLI Commands

#### `eccsim.py ml report-card`
- Required: `--model <model_dir>`
- Optional: `--out <path>` (default: `model_card.md`)
- Generates consolidated card from metrics, thresholds, uncertainty, and evaluation files.

#### `eccsim.py ml check-drift`
- Required: `--model <model_dir> --new-data <dataset_dir>`
- Optional: `--out <drift.json>`
- Optional: `--fail-on-drift`

### New Artifact: `drift.json`
- `population_stability_index: {<feature>: float}`
- `ood_rate_delta: float`
- `confidence_shift: float`
- `status: {drift_detected: bool, severity: string}`

---

## Detailed Flag Contract (Backwards Compatibility)

- All new behavior is gated behind explicit ML flags/subcommands.
- Non-ML commands and default output format remain unchanged.
- Existing ML commands continue to work with current defaults.
- Existing fields in:
  - `dataset.csv`
  - `dataset_schema.json`
  - `dataset_manifest.json`
  - `metrics.json`
  - `thresholds.json`
  remain present; only additive keys/files are introduced.

---

## Test Plan Mapped to Current Layout

## New tests to add under `tests/python/`

### 1) CLI and artifact compatibility
- **`test_ml_cli_flags_backward_compat.py`**
  - Verify old commands still run without new flags.
  - Verify unknown new flags fail with argparse error.
  - Verify non-ML command outputs are unchanged.

### 2) Policy-aware labels and training
- **`test_ml_policy_labels.py`**
  - Build dataset with each `--label-policy` and assert deterministic `label_code` per policy.
  - Verify `dataset_manifest.json` stores `label_policy` and utility weights.

### 3) Evaluation command smoke + schema
- **`test_ml_evaluate_cli.py`**
  - Train model, run `ml evaluate`, assert `evaluation.json` exists and schema keys are present.
  - Assert deterministic metrics for fixed seed.

### 4) Uncertainty and OOD behavior
- **`test_ml_uncertainty_ood.py`**
  - Train with each `--ood-method`; verify thresholds and uncertainty artifacts are emitted.
  - Create OOD row and assert fallback reason includes OOD path.

### 5) Selector overrides
- **`test_selector_ml_overrides.py`**
  - Verify `--ml-confidence-min` and `--ml-ood-max` override model defaults.
  - Verify `--ml-policy` switches advisory recommendation head only; final decision still constraint-safe.

### 6) Feature-pack gating
- **`test_ml_feature_pack.py`**
  - Build datasets with each feature pack and verify expected optional columns.
  - Verify training still succeeds with `core` pack and deterministic seed.

### 7) Drift check smoke
- **`test_ml_drift_check.py`**
  - Generate baseline model + new dataset, run drift check, assert `drift.json` schema.
  - Verify `--fail-on-drift` exit behavior.

## Existing tests to extend
- Extend `tests/python/test_ml_integration.py` with:
  - train→evaluate smoke
  - policy-specific deterministic checks
  - selector override checks.

- Extend golden coverage in:
  - `tests/python/test_golden_cli_outputs.py`
  - only for explicit ML command outputs (new fixtures), keeping non-ML goldens unchanged.

---

## Acceptance Criteria by Phase

### Phase 1
- New policy flags and evaluate command implemented.
- New additive manifest/metrics keys present.
- Deterministic tests pass with fixed seeds.

### Phase 2
- OOD method selectable and thresholded.
- Uncertainty artifact generated.
- Selector fallback paths fully covered by tests.

### Phase 3
- Feature packs produce deterministic optional columns.
- No regressions in existing ML or non-ML command behavior.

### Phase 4
- Drift command generates actionable status and nonzero signal under shifted data.
- Report-card command consolidates all artifacts.

---

## Suggested Delivery Sequence

1. Implement Phase 1 first (highest value, lowest risk).
2. Add Phase 2 uncertainty/OOD improvements once evaluate pipeline is stable.
3. Add feature packs in Phase 3 after metric baselines are captured.
4. Add lifecycle tooling (Phase 4) last.

This sequence maximizes incremental value while keeping every change additive and backwards-compatible.
