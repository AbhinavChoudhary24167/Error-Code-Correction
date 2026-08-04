from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import jsonschema

from validation.environment_doctor import (
    check_cpp_runtime_compatibility,
    check_python_command_consistency,
)


REPO = Path(__file__).resolve().parents[2]


def _runtime_file(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    runtime = directory / "libstdc++-6.dll"
    runtime.write_bytes(b"test runtime marker")
    return runtime


def test_windows_cpp_runtime_collision_is_actionable(tmp_path: Path) -> None:
    expected = _runtime_file(tmp_path / "toolchain")
    conflicting = _runtime_file(tmp_path / "other")

    result = check_cpp_runtime_compatibility(
        expected.parent / "g++.exe",
        path_value=str(conflicting.parent),
        system_name="Windows",
        executable_dir=tmp_path / "repo",
        toolchain_runtime=expected,
    )

    assert result["status"] == "error"
    assert result["details"]["resolved_runtime"] == str(conflicting.resolve())
    assert result["details"]["toolchain_runtime"] == str(expected.resolve())
    assert str(expected.parent.resolve()) in result["remediation"]


def test_windows_cpp_runtime_match_passes(tmp_path: Path) -> None:
    expected = _runtime_file(tmp_path / "toolchain")

    result = check_cpp_runtime_compatibility(
        expected.parent / "g++.exe",
        path_value=str(expected.parent),
        system_name="Windows",
        executable_dir=tmp_path / "repo",
        toolchain_runtime=expected,
    )

    assert result["status"] == "pass"
    assert result["details"]["resolved_runtime"] == str(expected.resolve())


def test_python_command_divergence_is_reported(tmp_path: Path) -> None:
    active = tmp_path / "primary" / "python.exe"
    alternate = tmp_path / "alternate" / "python3.exe"
    active.parent.mkdir(parents=True)
    alternate.parent.mkdir(parents=True)
    active.write_bytes(b"primary")
    alternate.write_bytes(b"alternate")

    result = check_python_command_consistency(
        active,
        python_command=active,
        python3_command=alternate,
        system_name="Windows",
    )

    assert result["status"] == "warning"
    assert result["details"]["active"] == str(active.resolve())
    assert result["details"]["python3"] == str(alternate.resolve())


def test_doctor_bootstraps_without_site_packages_and_matches_schema() -> None:
    result = subprocess.run(
        [sys.executable, "-S", "eccsim.py", "doctor", "--json"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)
    schema = json.loads(
        (REPO / "schemas" / "environment-doctor.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(report, schema)
    assert report["schema_version"] == 1
    assert any(item["id"] == "dependency:numpy" for item in report["checks"])


def test_doctor_is_listed_in_top_level_help() -> None:
    result = subprocess.run(
        [sys.executable, "eccsim.py", "--help"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "doctor" in result.stdout
