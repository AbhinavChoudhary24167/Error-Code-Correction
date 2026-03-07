"""Model report-card generation for ECC ML artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing required artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _format_md_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _dict_section(title: str, payload: dict[str, Any]) -> list[str]:
    lines = [f"## {title}", ""]
    for key in sorted(payload):
        lines.append(f"- `{key}`: {_format_md_value(payload[key])}")
    lines.append("")
    return lines


def generate_report_card(model_dir: Path, out_path: Path) -> dict[str, Path]:
    """Generate a consolidated markdown report-card from model artifacts.

    Relative output paths are resolved from the current working directory.
    """

    metrics = _read_json(model_dir / "metrics.json")
    thresholds = _read_json(model_dir / "thresholds.json")
    uncertainty = _read_json(model_dir / "uncertainty.json")

    evaluation_path = model_dir / "evaluation.json"
    evaluation = None
    if evaluation_path.is_file():
        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))

    resolved_out = out_path if out_path.is_absolute() else (Path.cwd() / out_path)
    resolved_out.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "# ECC ML Report Card",
        "",
        f"- Model directory: `{model_dir.resolve()}`",
        f"- Output path contract: relative `--out` paths are resolved from current working directory (`{Path.cwd()}`).",
        "",
    ]

    lines.extend(_dict_section("Training Metrics", metrics))
    lines.extend(_dict_section("Thresholds", thresholds))
    lines.extend(_dict_section("Uncertainty", uncertainty))

    if evaluation is None:
        lines.extend(
            [
                "## Evaluation",
                "",
                "- `status`: evaluation.json not found in model directory",
                "",
            ]
        )
    else:
        lines.extend(_dict_section("Evaluation", evaluation))

    resolved_out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"report_card": resolved_out}
