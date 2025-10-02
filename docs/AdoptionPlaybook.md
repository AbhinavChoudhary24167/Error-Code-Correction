# ECC Adoption Playbook

This playbook distils the repository into a quarter-scale deployment plan for chip teams that must balance reliability, performance, power, area (PPA), and carbon budgets.

## Required Inputs
- **Technology point**: node (nm), nominal VDD, junction temperature targets.
- **Soft-error characterisation**: `qcrit` lookup or SER curves, multi-bit upset preset (`mbu`), site altitude/latitude.
- **Memory configuration**: array capacity (GiB), word width, bitcell area.
- **Reliability baseline**: unprotected FIT budget, target FIT per TB-year, mission lifetime.
- **Sustainability context**: grid carbon intensity trajectory, embodied carbon factors (override defaults if available).

## Toolchain Outputs
Running `python analysis/workload_scenarios.py` and `python analysis/generate_figures.py` yields (artefacts are `.gitignore`d, so archive them per project):
- **Recommended ECC** per scenario, including dynamic duty-cycle and adaptive scrub studies (`reports/analysis/workload_scenarios.json`).
- **Frontier visualisations** covering carbon vs. FIT, GS robustness, and metric correlations (`reports/figures/*.png`).
- **Scorecards**: ESII, NESII, GS with percentile anchors for auditable decision logs.

## SLA Alignment
- Map the fleet FIT budget to `--constraints fit_max` when invoking `eccsim select` or when consuming `analysis/workload_scenarios.py` results.
- Verify that post-ECC FIT stays below 10 kFIT/TB-year (adjust threshold for workload-specific SLAs).
- Record the carbon delta between the winning code and the next-best feasible alternative to quantify sustainability opportunity cost.

## PPA / CO₂ Sign-off Checklist
1. **Parameter capture** – Freeze the inputs listed above and archive scenario JSON files alongside Git SHA.
2. **Static selector run** – Execute `eccsim select` with the frozen scenario to obtain baseline recommendations and Pareto frontier.
3. **Dynamic stress sweep** – Run `python analysis/workload_scenarios.py` to confirm duty-cycle and adaptive scrub behaviour; update fit budgets if excursions exceed SLA.
4. **Score reconciliation** – Regenerate figures via `python analysis/generate_figures.py`; embed GS ablation, carbon heatmap, and correlation plots in the review packet.
5. **Cross-functional review** – Present the checklist, FIT deltas, and carbon summaries to reliability, architecture, and sustainability stakeholders; capture sign-off in the project tracker.

Keeping this checklist under version control makes quarterly refreshes repeatable while exposing how design decisions evolve with workload and supply-chain assumptions.
