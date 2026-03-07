#!/usr/bin/env python3
"""Assemble and validate release signoff artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


MANDATORY_ARTIFACTS = {
    "calibration_envelope": "calibration_envelope.md",
    "provenance_manifest": "provenance_manifest.json",
    "uncertainty_report": "uncertainty_report.json",
    "holdout_metrics": "holdout_metrics.json",
    "drift_status": "drift_status.json",
    "compatibility_test_results": "compatibility_test_results.json",
}
SUMMARY_FILENAME = "summary.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_holdout_metrics(path: Path) -> tuple[bool, str]:
    payload = _read_json(path)
    signoff = payload.get("signoff")
    if isinstance(signoff, dict) and "pass" in signoff:
        passed = bool(signoff["pass"])
        return passed, "signoff.pass must be true"

    if "thresholds_pass" in payload:
        passed = bool(payload["thresholds_pass"])
        return passed, "thresholds_pass must be true"

    return False, "missing `signoff.pass` or `thresholds_pass`"


def _validate_drift_status(path: Path) -> tuple[bool, str]:
    payload = _read_json(path)

    actions = payload.get("actions")
    if isinstance(actions, dict) and "action" in actions:
        action = str(actions["action"])
        return action != "fail", "drift policy action must not be `fail`"

    status = payload.get("status", {})
    if isinstance(status, dict):
        severity = str(status.get("severity", "none"))
        drift_detected = bool(status.get("drift_detected", False))
        if severity == "high":
            return False, "drift severity must not be `high`"
        if drift_detected and severity not in {"none", "low", "medium"}:
            return False, "drift status severity is invalid"
        return True, "drift status severity must not be `high`"

    return False, "missing drift status fields"


def _validate_compatibility_results(path: Path) -> tuple[bool, str]:
    payload = _read_json(path)
    if "pass" in payload:
        return bool(payload["pass"]), "compatibility `pass` must be true"
    if "failed" in payload:
        return int(payload["failed"]) == 0, "compatibility `failed` must be 0"
    return False, "missing `pass` or `failed` compatibility fields"


def _write_summary(out_path: Path, *, version: str, statuses: list[dict[str, Any]]) -> None:
    lines = [
        "# Executive Summary",
        "",
        f"Release candidate `{version}` includes all required signoff artifacts for reviewer signoff.",
        "",
        "## Plain-language interpretation",
        "",
        "- **Calibration envelope:** Confirms where the model is valid (node, voltage, temperature, and corner limits).",
        "- **Provenance manifest:** Records exactly where calibration data came from, so reviewers can trace inputs.",
        "- **Uncertainty report:** Quantifies model uncertainty so decisions are not based on false precision.",
        "- **Holdout metrics:** Shows the model still meets numerical quality thresholds on unseen data.",
        "- **Drift status:** Checks whether new data has shifted enough to reduce trust in predictions.",
        "- **Compatibility results:** Confirms legacy/contract tests still pass, preserving backward compatibility.",
        "",
        "## Gate results",
        "",
    ]
    for status in statuses:
        mark = "✅" if status["pass"] else "❌"
        lines.append(f"- {mark} `{status['artifact']}`: {status['message']}")

    failing = [s for s in statuses if not s["pass"]]
    lines += [
        "",
        "## Release readiness",
        "",
        "- **Result:** " + ("PASS" if not failing else "FAIL"),
        "- **Reasoning:** "
        + (
            "All mandatory artifacts are present and quality gates passed; outputs make literal sense for reviewer signoff."
            if not failing
            else "At least one mandatory artifact is missing or failed a threshold gate; release is blocked until corrected."
        ),
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _default_version(repo_root: Path) -> str:
    version_file = repo_root / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()
    return "unversioned"


def build_signoff_package(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    version = args.version or _default_version(repo_root)
    out_root = Path(args.out_root)
    out_dir = (out_root / version).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = {
        "calibration_envelope": Path(args.calibration_envelope),
        "provenance_manifest": Path(args.provenance_manifest),
        "uncertainty_report": Path(args.uncertainty_report),
        "holdout_metrics": Path(args.holdout_metrics),
        "drift_status": Path(args.drift_status),
        "compatibility_test_results": Path(args.compatibility_test_results),
    }

    for name, src in sources.items():
        if not src.is_file():
            raise FileNotFoundError(f"Missing mandatory signoff artifact `{name}`: {src}")
        shutil.copy2(src, out_dir / MANDATORY_ARTIFACTS[name])

    holdout_pass, holdout_msg = _validate_holdout_metrics(out_dir / MANDATORY_ARTIFACTS["holdout_metrics"])
    drift_pass, drift_msg = _validate_drift_status(out_dir / MANDATORY_ARTIFACTS["drift_status"])
    compat_pass, compat_msg = _validate_compatibility_results(
        out_dir / MANDATORY_ARTIFACTS["compatibility_test_results"]
    )

    statuses = [
        {
            "artifact": MANDATORY_ARTIFACTS["holdout_metrics"],
            "pass": holdout_pass,
            "message": holdout_msg,
        },
        {
            "artifact": MANDATORY_ARTIFACTS["drift_status"],
            "pass": drift_pass,
            "message": drift_msg,
        },
        {
            "artifact": MANDATORY_ARTIFACTS["compatibility_test_results"],
            "pass": compat_pass,
            "message": compat_msg,
        },
    ]

    manifest = {
        "version": version,
        "artifacts": {k: v for k, v in MANDATORY_ARTIFACTS.items()},
        "status": statuses,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _write_summary(out_dir / SUMMARY_FILENAME, version=version, statuses=statuses)

    failing = [s for s in statuses if not s["pass"]]
    if failing:
        raise RuntimeError(
            "Signoff package failed gates: " + ", ".join(f"{item['artifact']} ({item['message']})" for item in failing)
        )

    print(str(out_dir))
    return 0


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=None, help="Signoff package version (defaults to VERSION file).")
    parser.add_argument(
        "--out-root",
        default=str(repo_root / "reports" / "signoff"),
        help="Output root directory for signoff package versions.",
    )
    parser.add_argument(
        "--calibration-envelope",
        default=str(repo_root / "docs" / "calibration_signoff_envelope.md"),
        help="Path to calibration envelope artifact.",
    )
    parser.add_argument(
        "--provenance-manifest",
        default=str(repo_root / "reports" / "calibration" / "provenance_manifest.json"),
        help="Path to provenance manifest artifact.",
    )
    parser.add_argument(
        "--uncertainty-report",
        default=str(repo_root / "tech_calib_uncertainty.json"),
        help="Path to uncertainty report artifact.",
    )
    parser.add_argument("--holdout-metrics", required=True, help="Path to holdout metrics JSON artifact.")
    parser.add_argument("--drift-status", required=True, help="Path to drift status JSON artifact.")
    parser.add_argument(
        "--compatibility-test-results",
        required=True,
        help="Path to compatibility test results JSON artifact.",
    )
    args = parser.parse_args()
    return build_signoff_package(args)


if __name__ == "__main__":
    raise SystemExit(main())
