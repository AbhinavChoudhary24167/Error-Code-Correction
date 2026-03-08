# Error-Code-Correction (ECC) Design & Analysis Framework

This repository is a research-grade ECC analysis framework that links **reliability**, **energy**, **carbon**, and **selection decisions** for SRAM-oriented design studies. It is intended for:

- thesis appendix and methodology reproducibility,
- GitHub research publication,
- reviewer replay checks,
- future engineering handoff.

The framework is intentionally **deterministic-first**: baseline analytical/physics-inspired selection remains authoritative, while ML is strictly advisory.

---

## 1) System overview

### 1.1 Why this framework exists

Conventional ECC comparison usually stops at correction capability (e.g., SEC-DED vs BCH). Real deployment requires coupled decisions:

- What post-ECC reliability do we get?
- What decode/scrub energy is consumed?
- What carbon burden does that imply (operational + embodied)?
- Which ECC sits on the best trade-off frontier under constraints?

This repository operationalizes those questions with a stable CLI and regression-tested outputs.

### 1.2 Module interaction map

1. **Reliability / SER modeling** (`ser_model.py`, `fit.py`, `mbu.py`, `qcrit_loader.py`) generates reliability metrics such as FIT and post-correction behavior.
2. **Energy model** (`energy_model.py`) maps ECC primitive operations to calibrated gate energies (J), then derives operation/scrub energy.
3. **Carbon model** (`carbon_model.py`, legacy `carbon.py`) maps area/energy into embodied + operational + total carbon (kgCO2e).
4. **Selector** (`ecc_selector.py`) ranks candidates through deterministic multi-objective logic (Pareto + decision rules).
5. **CLI orchestrator** (`eccsim.py`) exposes reproducible workflows.
6. **Telemetry parser** (`parse_telemetry.py`) validates normalized telemetry schema and computes EPC from measured toggles.
7. **ML advisory stack** (`ml/`) trains/evaluates advisory models, with OOD and confidence gating and deterministic fallback.

---

## 2) Major file technical guide

## 2.1 `energy_model.py`

### Why XOR/AND/adder abstraction is used

ECC decoders can be represented as counts of primitive logic operations (XOR checks, AND checks, locator additions). This enables a controllable model that preserves code-level complexity differences while avoiding transistor-level simulation cost. The code implements this via primitive gate energies and per-code primitive counts.

### Why technology calibration is loaded from `tech_calib.json`

Calibration is loaded at import (`_CALIB = load_calibration(...)`) to bind node/VDD energy values to a versioned data artifact, keeping runtime behavior deterministic and testable across commands.

### Why nearest-voltage interpolation exists

`gate_energy_vec(..., mode='nearest')` preserves backward-compatible behavior when users want strict snapping to available calibration points. The default `pwl` mode performs piecewise-linear interpolation; nearest mode is retained as legacy-compatible lookup and logs rounding when needed.

### Physical meaning of core functions

- `gate_energy(node_nm, vdd, gate)` → per-operation energy for a primitive gate (J/op).
- `gate_energy_vec(...)` → vectorized interpolation across VDD values for the selected gate and node interpolation path.
- `estimate_energy(parity_bits, detected_errors, ...)` → read-side ECC energy estimate from XOR and AND counts (J).
- `epc(xor_cnt, and_cnt, corrections, ...)` → energy per corrected bit (J/bit).

### Governing formulas and units

- Gate energy from calibration/interpolation:
  \[
  E_g = E_g(\text{node}, V_{DD}) \quad [\text{J/op}]
  \]
- Read operation energy:
  \[
  E_{read} = N_{xor}E_{xor} + N_{and}E_{and} \quad [\text{J}]
  \]
- Energy per correction:
  \[
  EPC = \frac{E_{total}}{N_{corr}} \quad [\text{J/bit}]
  \]

### Engineering assumptions

- Gate-level abstraction is used instead of transistor-level power simulation.
- Node dependence is injected from calibration tables rather than compact-model solving.
- VDD dependence uses nearest or piecewise-linear interpolation to approximate scaling while preserving CLI determinism.

---

## 2.2 `carbon_model.py`

### Model components

- **Embodied carbon**: static fabrication burden from effective area × fab intensity × yield loss.
- **Operational carbon**: dynamic burden from lifetime energy and grid factor (kgCO2e/kWh).
- **Total carbon**: embodied + operational over lifetime.

### Why node scaling affects embodied carbon

`_resolve_node` maps requested node to exact or nearest calibrated node; node defaults carry different fab intensity and yield assumptions, so embodied burden changes with node technology.

### Fab intensity and carbon intensity meanings

- **Fab intensity** (kgCO2e/cm²): embodied carbon per manufactured silicon area.
- **Grid/carbon intensity** (kgCO2e/kWh): operational emissions per consumed electrical energy.

### Formulas and units

- Embodied:
  \[
  C_{emb} = A_{cm^2} \cdot I_{fab} \cdot Y_{loss} \quad [\text{kgCO2e}]
  \]
- Operational:
  \[
  E_{kWh} = \frac{E_J}{3.6\times10^6},\quad C_{op}=E_{kWh}\cdot CI_{grid} \quad [\text{kgCO2e}]
  \]
- Total:
  \[
  C_{tot}=C_{emb}+C_{op}
  \]

### Embodied vs operational tradeoff (SRAM context)

For SRAM macros, larger area and advanced-node manufacturing assumptions can dominate embodied carbon, while aggressive scrub/reliability policy can increase operational energy and thus operational carbon. The framework surfaces both terms explicitly instead of collapsing them prematurely.

---

## 2.3 `ecc_selector.py`

### ECC selection logic

`select(...)` computes per-code records (FIT, carbon, latency, ESII/NESII), filters constraints, computes Pareto fronts, then applies deterministic decision rules (knee, epsilon-constraint, or explicit carbon policy).

### Ranking criteria

Primary minimized axes for Pareto/non-dominated logic:

- `FIT` (reliability risk),
- `carbon_kg` (sustainability burden),
- `latency_ns` (performance overhead).

### BER/burst/correction capability role

Reliability backend uses SER/FIT and MBU assumptions; correction capability enters via ECC coverage behavior and per-code characteristics in `_CODE_DB` / supporting reliability helpers, affecting post-ECC FIT and resulting rank position.

### Sustainability weighting and deterministic baseline

`ESII/NESII` are computed per candidate; decision policy can prioritize carbon modes, but deterministic selector remains primary in this repository’s baseline path and output contracts.

### ML advisory fallback logic

When used through `ecc_selector.py --ml-model`, ML recommendation is accepted only if confidence/OOD gates pass; otherwise fallback reason is emitted and final decision stays with deterministic baseline.

### Scientific meaning of key output fields

- `FIT`: predicted failures-in-time post-policy/post-ECC.
- `carbon_kg`: total carbon proxy used by selector objective.
- `latency_ns`: decoding/logic latency model proxy.
- `ESII`, `NESII`: sustainability-integrated indices.
- `pareto`: non-dominated feasible set.
- `decision`: deterministic mode and parameters used.
- `quality.hypervolume`, `quality.spacing`: frontier quality indicators.
- `scenario_hash`: reproducibility fingerprint for scenario inputs.

---

## 2.4 `parse_telemetry.py`

### Telemetry CSV schema

Canonical required fields are fixed and ordered (`workload_id`, `node_nm`, `vdd`, `tempC`, `clk_MHz`, `xor_toggles`, `and_toggles`, `add_toggles`, `corr_events`, `words`, `accesses`, `scrub_s`, `capacity_gib`, `runtime_s`).

### XOR/AND/corrections meaning

- `xor_toggles`: parity/syndrome XOR activity count.
- `and_toggles`: logic gating/candidate validation activity count.
- `corr_events`: number of corrected events/bits (per telemetry definition).

`compute_epc` sums XOR/AND toggles and divides estimated total energy by total corrections to derive EPC (J/bit).

### Why telemetry-derived EPC matters

It ties model-based energy primitives to measured workload logic activity, enabling scientific comparison across workloads beyond static per-word assumptions.

---

## 2.5 ML workflow (`ml/`)

### Why ML is advisory only

Repository policy keeps deterministic selector authoritative for backward compatibility and interpretability. ML outputs are optional add-ons, never silent replacements.

### Confidence and OOD handling

`ml/predict.py` resolves thresholds (`confidence_min`, `ood_threshold`, policy), computes confidence from classifier probabilities, computes OOD score (z-score/mahalanobis/iforest), and flags low-confidence/OOD predictions for fallback handling.

### Threshold interpretation

- **confidence threshold (`confidence_min`)**: minimum posterior confidence to trust advisory output.
- **OOD threshold (`ood_threshold`)**: maximum allowed distribution-distance score.
- If either gate fails, prediction is rejected and deterministic fallback is expected.

### Uncertainty interpretation

Low confidence or high OOD score indicates insufficient in-distribution evidence for that scenario; fallback preserves robustness and reproducibility.

---

## 3) CLI technical documentation

Below are stable command entry points and interpretation notes.

## 3.1 Energy

```bash
python3 eccsim.py energy --code <sec-ded|sec-daec|taec|polar> --node <nm> --vdd <V> --temp <C> --ops <count> --lifetime-h <hours>
```

- `--code`: ECC family for primitive-count model.
- `--node`, `--vdd`: operating point used for gate energy interpolation.
- `--ops`: number of ECC operations.
- `--lifetime-h`: leakage accumulation horizon.

Output includes Dynamic (J), Leakage (J), Total (J). Interpretation: dynamic responds to operation counts; leakage scales with area proxy and lifetime.

## 3.2 Carbon

```bash
python3 eccsim.py carbon --areas <logic_mm2,macro_mm2> --alpha <logic_alpha,macro_alpha> --ci <kgCO2e/kWh> --Edyn <kWh> --Eleak <kWh>
```

Legacy mode output: embodied, operational, total carbon.

Calibrated mode (additive behavior):

```bash
python3 eccsim.py carbon --calibrated --node <nm> --area-cm2 <cm2> --grid-region <region> --years <y> --accesses-per-day <n> --areas ... --alpha ... --ci ... --Edyn ... --Eleak ...
```

Interpretation: embodied reflects fabrication assumptions; operational reflects grid and workload energy scaling.

## 3.3 ESII

```bash
python3 eccsim.py esii --fit-base <FIT> --fit-ecc <FIT> --e-dyn-j <J> --e-leak-j <J> --ci <kgCO2e/kWh> --embodied-kgco2e <kg> --basis <per_gib|system>
```

Interpretation: ESII/NESII combine reliability improvement and carbon/energy burdens into integrated sustainability-style scores.

## 3.4 Selection

```bash
python3 eccsim.py select --codes <comma-list> --node <nm> --vdd <V> --temp <C> --mbu <none|light|moderate|heavy> --capacity-gib <GiB> --ci <kgCO2e/kWh> --bitcell-um2 <um2>
```

Optional constraint syntax:

```bash
--constraints fit_max=<v>,latency_ns_max=<v>,carbon_kg_max=<v>
```

Interpretation: deterministic multi-objective recommendation across FIT/carbon/latency. Use `--emit-candidates` for machine-readable per-candidate records.

## 3.5 Reliability

```bash
python3 eccsim.py reliability hazucha --qcrit <pC> --qs <pC> --area <mm2> [--alt-km ... --latitude ...]
```

Returns SER-like scalar from the Hazucha-style model path; engineering interpretation is relative soft-error sensitivity under specified charge/area/environment assumptions.

## 3.6 ML

```bash
python3 eccsim.py ml train --dataset <dir> --model-out <dir>
python3 eccsim.py ml evaluate --dataset <dir> --model <dir> --out <dir>
python3 eccsim.py ml report-card --model <dir> --out <path>
```

Recommended sequence for reproducible evaluation:

1. `ml build-dataset`
2. `ml split-dataset`
3. `ml train`
4. `ml evaluate`
5. `ml report-card`

---

## 4) Clean-environment execution guide

## 4.1 Environment

- Python: `3.10+` recommended.
- Build/tooling: `make`, C++ compiler toolchain.
- Python dependencies from `requirements.txt`.

## 4.2 Setup commands

```bash
git clone <repo>
cd Error-Code-Correction
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## 4.3 Build + tests + smoke

```bash
make
make test
python3 -m pytest -q
bash tests/smoke_test.sh
```

---

## 5) Executed example outputs (from current code)

The following were executed on this repository revision; values are **actual CLI outputs**, not fabricated.

## 5.1 Energy estimation

Command:

```bash
python3 eccsim.py energy --code sec-ded --node 7 --vdd 0.8 --temp 45 --ops 1000000 --lifetime-h 8760
```

Output:

```text
Dynamic (J)     1.400e-04
Leakage (J)     6.357e+00
Total (J)       6.357e+00
```

Interpretation: leakage dominates for this long-lifetime scenario.

## 5.2 Carbon estimation

Command:

```bash
python3 eccsim.py carbon --areas 0.1,0.2 --alpha 120,140 --ci 0.55 --Edyn 0.01 --Eleak 0.02
```

Output:

```text
Embodied (kgCO2e)    40.000
Operational (kgCO2e) 0.017
Total (kgCO2e)       40.017
```

Interpretation: embodied term dominates under the supplied area/alpha assumptions.

## 5.3 ECC selection

Command:

```bash
python3 eccsim.py select --codes sec-ded-64,sec-daec-64,taec-64,bch-63 --node 7 --vdd 0.8 --temp 45 --mbu moderate --capacity-gib 16 --ci 400 --bitcell-um2 0.08
```

Output:

```text
carbon cap fallback to max for N<5
NESII normalization fallback to min-max
bch-63 ESII=0.0654 NESII=100.00 GS=2.77
```

Interpretation: in this scenario, selector deterministic decision chooses BCH candidate under its multi-objective rules and normalization path.

## 5.4 Telemetry EPC

Command (schema-valid example row):

```bash
python3 - <<'PY'
from parse_telemetry import compute_epc
te,epc=compute_epc('/tmp/telemetry_demo.csv')
print(f'Total energy (J): {te:.3e}')
print(f'EPC (J/bit): {epc:.3e}')
PY
```

Output:

```text
Total energy (J): 2.500e-11
EPC (J/bit): 2.500e-11
```

Interpretation: one correction event with modest toggle counts yields identical total and EPC values.

## 5.5 ML advisory output (with fallback)

Command:

```bash
python3 ecc_selector.py --ml-model /tmp/ml_model --node 14 --vdd 0.8 --temp 75 --capacity-gib 8 --ci 0.55 --bitcell-um2 0.04 --json
```

Key output fields:

```json
{
  "baseline_recommendation": "bch-63",
  "ml_recommendation": null,
  "fallback_used": true,
  "fallback_reason": "No admissible ML suggestion (OOD/low confidence); using baseline",
  "final_decision": "bch-63",
  "confidence": 0.0,
  "selected_policy": "carbon_min"
}
```

Interpretation: ML gating rejected advisory output (confidence/OOD), so deterministic baseline remained final decision.

---

## 6) Scientific result interpretation guide

### Why values appear

- **Energy values** arise from calibrated gate energies + primitive counts + leakage area/lifetime scaling.
- **Carbon values** arise from embodied fabrication assumptions and energy-to-carbon conversion via grid intensity.
- **Selection choice** arises from deterministic multi-objective rule chain (feasibility → Pareto/NSGA metadata → policy/knee decision).

### Internal model provenance by metric

- `FIT`: SER/FIT chain in reliability modules.
- `E_*`: energy model dynamic/leakage/scrub paths.
- `carbon_*`: carbon model + legacy carbon composition paths.
- `ESII/NESII`: sustainability scoring composition.

### Design implications

- TAEC may outperform Hamming-like options on reliability but may incur higher latency/energy/carbon depending on scenario assumptions.
- Lower-carbon options may require accepting weaker reliability margin or different scrub policy.
- High-reliability codes can shift embodied/operational balance due to extra logic/macro assumptions.

---

## 7) Practical use cases

## 7.1 SRAM design engineer

Goal: choose ECC under BER/FIT target.

1. Run `select` with candidate set and constraints.
2. Export `--emit-candidates` and inspect FIT/carbon/latency tradeoffs.
3. Validate final choice against latency and scrub policy.

## 7.2 Sustainability researcher

Goal: compare embodied vs operational burden.

1. Run `carbon` in legacy and calibrated modes.
2. Vary grid region/intensity and lifetime scaling.
3. Report `static` vs `dynamic` fractions and uncertainty bounds.

## 7.3 Reliability engineer

Goal: interpret correction capability impact.

1. Use reliability and selection flows under varying MBU/severity.
2. Compare post-ECC FIT and feasible set movement.
3. Examine implications of stricter `fit_max` constraints.

## 7.4 ML-assisted advisory flow

Goal: assess if ML can assist scenario triage.

1. Build/split/train/evaluate model.
2. Run `ecc_selector.py --ml-model ...` with scenario.
3. Use advisory only when confidence high and OOD low; otherwise trust deterministic baseline.

---

## 8) Assumptions and limitations

### Assumptions

- Gate-level energy abstraction is representative enough for comparative ECC analysis.
- Node/VDD interpolation between calibrated points is acceptable for scenario sweeps.
- Carbon calibration defaults encode representative (not universal) fab/grid assumptions.
- ML data distribution is bounded by generated/available scenario artifacts.

### Limitations

- Not a transistor/SPICE-level power model.
- Not a full foundry lifecycle assessment tool.
- Advisory ML can reject many edge scenarios due to confidence/OOD gating.
- Some selector metrics are simplified proxies intended for comparative ranking, not tapeout signoff.

---

## 9) Technical conclusion

This framework’s core strength is **cross-domain coupling with deterministic reproducibility**: reliability, energy, carbon, and selection outputs are generated through a stable, test-guarded CLI contract. Scientifically, it is strongest as a **comparative architecture-decision engine** rather than an absolute silicon signoff model. The models intentionally simplify device physics and manufacturing complexity into calibrated surrogates, which is appropriate for early-stage design-space exploration, policy analysis, and research reproducibility. Future extension is naturally additive: richer calibration datasets, broader ECC families, tighter uncertainty quantification, and improved ML explainability can be incorporated without breaking baseline deterministic behavior.

