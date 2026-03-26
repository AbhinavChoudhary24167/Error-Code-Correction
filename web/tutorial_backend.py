"""Generate onboarding tutorial cases for the static web dashboard.

This module computes deterministic, backend-style what-if cases from repository
Pareto artifacts so the dashboard can teach new users how tuning levers affects
trade-offs.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "web"
DATASET_MANIFEST = WEB_DIR / "datasets.json"
TUTORIAL_OUTPUT = WEB_DIR / "tutorial_cases.json"


@dataclass(frozen=True)
class CaseTemplate:
    case_id: str
    title: str
    lever: str
    lever_effect: str
    fit_scale: float
    carbon_scale: float
    latency_scale: float


CASE_TEMPLATES = [
    CaseTemplate(
        case_id="reliability_guardband",
        title="Reliability Guardband",
        lever="Tighten reliability policy",
        lever_effect="Shorter scrub window and conservative recovery margin.",
        fit_scale=0.62,
        carbon_scale=1.09,
        latency_scale=1.03,
    ),
    CaseTemplate(
        case_id="carbon_saver",
        title="Carbon Saver",
        lever="Relax carbon-sensitive operating mode",
        lever_effect="Lower activity budget with reduced scrub duty cycle.",
        fit_scale=1.32,
        carbon_scale=0.81,
        latency_scale=0.98,
    ),
    CaseTemplate(
        case_id="latency_first",
        title="Latency First",
        lever="Prioritize fast decode path",
        lever_effect="Aggressive decode pipeline; moderate reliability trade-off.",
        fit_scale=1.18,
        carbon_scale=1.03,
        latency_scale=0.82,
    ),
]


def _parse_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _read_first_pareto_row(pareto_path: Path) -> dict[str, Any]:
    with pareto_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            return row
    return {}


def _inference_text(case: CaseTemplate, fit: float, carbon: float, latency: float) -> str:
    return (
        f"{case.title} predicts FIT={fit:.2e}, carbon={carbon:.3f} kg/GiB, "
        f"latency={latency:.3f} ns. Use this mode when '{case.lever}' aligns "
        "with program priorities."
    )


def generate_tutorial_cases() -> dict[str, Any]:
    manifest = json.loads(DATASET_MANIFEST.read_text(encoding="utf-8"))
    output: dict[str, Any] = {
        "generated_from": str(DATASET_MANIFEST.relative_to(REPO_ROOT)),
        "datasets": {},
    }

    for dataset_key, info in manifest.items():
        pareto_rel = Path(info["pareto"])
        pareto_path = (WEB_DIR / pareto_rel).resolve()
        base_row = _read_first_pareto_row(pareto_path)

        base_fit = _parse_float(base_row.get("fit"), 0.0)
        base_carbon = _parse_float(base_row.get("carbon_kg"), 0.0)
        base_latency = _parse_float(base_row.get("latency_ns"), 0.0)

        cases = []
        for template in CASE_TEMPLATES:
            fit = base_fit * template.fit_scale
            carbon = base_carbon * template.carbon_scale
            latency = base_latency * template.latency_scale
            cases.append(
                {
                    "id": template.case_id,
                    "title": template.title,
                    "lever": template.lever,
                    "lever_effect": template.lever_effect,
                    "result": {
                        "fit": fit,
                        "carbon_kg": carbon,
                        "latency_ns": latency,
                    },
                    "inference": _inference_text(template, fit, carbon, latency),
                }
            )

        output["datasets"][dataset_key] = {
            "label": info.get("label", dataset_key),
            "baseline": {
                "fit": base_fit,
                "carbon_kg": base_carbon,
                "latency_ns": base_latency,
            },
            "cases": cases,
        }

    return output


def main() -> None:
    payload = generate_tutorial_cases()
    TUTORIAL_OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {TUTORIAL_OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
