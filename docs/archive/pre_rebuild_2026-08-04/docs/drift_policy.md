# ML Drift Policy

This document defines the drift metrics, thresholds, and action policy for `eccsim.py ml check-drift`.

## Metrics

The baseline `drift.json` report remains schema-stable and includes:

- **PSI-like feature drift** (`population_stability_index` + `summary.max_psi`)
  - Computed per numeric feature from binned reference-vs-new distributions.
  - `summary.max_psi` is used for policy gating.
- **Confidence shift** (`confidence_shift`)
  - Delta of new mean prediction confidence against training reference confidence.
- **OOD rate delta** (`ood_rate_delta`)
  - Delta between new OOD hit rate and training reference OOD rate.

## Thresholds

Policy thresholds use absolute values for PSI and OOD delta. Confidence gating is one-sided for confidence drops:

- **PSI-like max drift (`summary.max_psi`)**
  - warn: `>= 0.20`
  - fail: `>= 0.30`
- **Confidence shift (drop only: `max(0, -confidence_shift)`)**
  - warn: `>= 0.10`
  - fail: `>= 0.20`
- **OOD rate delta (`abs(ood_rate_delta)`)**
  - warn: `>= 0.05`
  - fail: `>= 0.10`

## Policy Actions

Policy action is resolved as:

1. **fail threshold**: any metric at/above fail threshold → `action=fail`
2. **warn threshold**: otherwise, any metric at/above warn threshold → `action=warn`
3. otherwise → `action=none`

Retraining recommendation is tied to action severity:

- `action=none` → `retrain_recommended=false`
- `action=warn` or `action=fail` → `retrain_recommended=true`

## Backward Compatibility Rules

- `drift.json` output schema is unchanged by default.
- New policy fields are emitted only in a **separate report file** when
  `--drift-policy-out <path>` is provided.
- Existing CLI formatting and default output remain unchanged.
