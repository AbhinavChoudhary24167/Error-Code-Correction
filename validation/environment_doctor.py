"""Cross-platform development-environment diagnostics.

The doctor deliberately depends only on the Python standard library so it can
run before the project's scientific Python dependencies are installed.
"""

from __future__ import annotations

import argparse
from importlib import metadata
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Mapping, Sequence


DOCTOR_SCHEMA_VERSION = 1
REQUIRED_DISTRIBUTIONS = (
    ("numpy", None),
    ("pandas", None),
    ("pytest", None),
    ("jsonschema", None),
    ("matplotlib", None),
    ("PyYAML", None),
    ("scikit-learn", "1.7.2"),
)
REQUIRED_PROJECT_FILES = (
    "VERSION",
    "tech_calib.json",
    "carbon_calib.json",
    "data/qcrit_sram6t.json",
)


def _check(
    check_id: str,
    status: str,
    summary: str,
    *,
    details: Mapping[str, str] | None = None,
    remediation: str | None = None,
) -> dict:
    result = {
        "id": check_id,
        "status": status,
        "summary": summary,
        "details": dict(details or {}),
    }
    if remediation is not None:
        result["remediation"] = remediation
    return result


def _run_tool(command: Sequence[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _first_path_file(
    filename: str,
    path_value: str,
    *,
    separator: str,
    executable_dir: Path | None = None,
) -> Path | None:
    search_dirs: list[Path] = []
    if executable_dir is not None:
        search_dirs.append(executable_dir)
    for raw_entry in path_value.split(separator):
        entry = raw_entry.strip().strip('"')
        if entry:
            search_dirs.append(Path(entry))
    for directory in search_dirs:
        candidate = directory / filename
        if candidate.is_file():
            return candidate.resolve()
    return None


def _gnu_runtime_for_compiler(compiler: Path) -> Path | None:
    adjacent = compiler.resolve().parent / "libstdc++-6.dll"
    if adjacent.is_file():
        return adjacent.resolve()
    result = _run_tool([str(compiler), "-print-file-name=libstdc++-6.dll"])
    if result is None or result.returncode != 0:
        return None
    value = result.stdout.strip()
    if not value or value == "libstdc++-6.dll":
        return None
    candidate = Path(value)
    return candidate.resolve() if candidate.is_file() else None


def check_cpp_runtime_compatibility(
    compiler: Path | None,
    *,
    path_value: str,
    system_name: str,
    executable_dir: Path | None = None,
    toolchain_runtime: Path | None = None,
) -> dict:
    """Check whether Windows will load the runtime matching ``compiler``.

    ``toolchain_runtime`` is injectable so the path-ordering logic can be
    tested without invoking a compiler.
    """

    if system_name != "Windows":
        return _check(
            "cpp_runtime",
            "skipped",
            "GNU C++ runtime collision check is only required on Windows",
        )
    if compiler is None:
        return _check(
            "cpp_runtime",
            "skipped",
            "GNU C++ runtime could not be checked because g++ is unavailable",
        )

    expected = toolchain_runtime or _gnu_runtime_for_compiler(compiler)
    if expected is None:
        return _check(
            "cpp_runtime",
            "warning",
            "Could not resolve the GNU C++ runtime associated with g++",
            details={"compiler": str(compiler)},
            remediation="Check the g++ installation and its -print-file-name output.",
        )

    loaded = _first_path_file(
        "libstdc++-6.dll",
        path_value,
        separator=";",
        executable_dir=executable_dir,
    )
    if loaded is None:
        return _check(
            "cpp_runtime",
            "error",
            "libstdc++-6.dll is not discoverable by Windows",
            details={
                "compiler": str(compiler),
                "toolchain_runtime": str(expected),
            },
            remediation=f"Prepend {expected.parent} to PATH before running native binaries.",
        )

    expected_resolved = expected.resolve()
    if str(loaded).casefold() != str(expected_resolved).casefold():
        return _check(
            "cpp_runtime",
            "error",
            "Windows resolves a libstdc++ runtime that does not match g++",
            details={
                "compiler": str(compiler),
                "resolved_runtime": str(loaded),
                "toolchain_runtime": str(expected_resolved),
            },
            remediation=(
                f"Prepend {expected_resolved.parent} to PATH before running native binaries "
                "or link the GNU runtimes statically."
            ),
        )

    return _check(
        "cpp_runtime",
        "pass",
        "Windows resolves the GNU C++ runtime associated with g++",
        details={
            "compiler": str(compiler),
            "resolved_runtime": str(loaded),
            "toolchain_runtime": str(expected_resolved),
        },
    )


def _check_python(executable: str) -> dict:
    version = platform.python_version()
    if sys.version_info < (3, 10):
        return _check(
            "python",
            "error",
            f"Python {version} is older than the required Python 3.10",
            details={"executable": executable, "version": version},
            remediation="Use a Python 3.10 or newer virtual environment.",
        )
    return _check(
        "python",
        "pass",
        f"Python {version} satisfies the Python 3.10+ requirement",
        details={"executable": executable, "version": version},
    )


def check_python_command_consistency(
    active_executable: Path,
    *,
    python_command: Path | None,
    python3_command: Path | None,
    system_name: str,
) -> dict:
    """Report when common Python command names select different runtimes."""

    commands = {"active": active_executable.resolve()}
    if python_command is not None:
        commands["python"] = python_command.resolve()
    if python3_command is not None:
        commands["python3"] = python3_command.resolve()

    normalise = (lambda value: str(value).casefold()) if system_name == "Windows" else str
    unique_paths = {normalise(value) for value in commands.values()}
    details = {name: str(path) for name, path in commands.items()}
    if len(unique_paths) > 1:
        return _check(
            "python_commands",
            "warning",
            "Common Python command names resolve to different interpreters",
            details=details,
            remediation=(
                "Activate one virtual environment and use its `python -m ...` commands "
                "consistently."
            ),
        )
    return _check(
        "python_commands",
        "pass",
        "Available Python command names resolve to the active interpreter",
        details=details,
    )


def _check_distribution(name: str, expected_version: str | None) -> dict:
    check_id = f"dependency:{name}"
    try:
        installed = metadata.version(name)
    except metadata.PackageNotFoundError:
        return _check(
            check_id,
            "error",
            f"Required Python distribution {name} is not installed",
            remediation="Install project dependencies with `python -m pip install -r requirements.txt`.",
        )
    if expected_version is not None and installed != expected_version:
        return _check(
            check_id,
            "error",
            f"{name} {installed} does not match the required {expected_version}",
            details={"installed": installed, "required": expected_version},
            remediation="Install project dependencies with `python -m pip install -r requirements.txt`.",
        )
    return _check(
        check_id,
        "pass",
        f"{name} {installed} is installed",
        details={"installed": installed},
    )


def _check_tool(name: str, *, required: bool) -> tuple[dict, Path | None]:
    resolved = shutil.which(name)
    if resolved is None:
        status = "error" if required else "skipped"
        qualifier = "Required" if required else "Optional"
        remediation = f"Install {name} and ensure it is available on PATH." if required else None
        return (
            _check(
                f"tool:{name}",
                status,
                f"{qualifier} tool {name} is not available on PATH",
                remediation=remediation,
            ),
            None,
        )

    result = _run_tool([resolved, "--version"])
    version_line = ""
    if result is not None:
        output = (result.stdout or result.stderr).strip().splitlines()
        version_line = output[0] if output else ""
    return (
        _check(
            f"tool:{name}",
            "pass",
            f"{name} is available",
            details={"path": resolved, "version": version_line},
        ),
        Path(resolved),
    )


def _check_project_files(repo_root: Path) -> dict:
    missing = [relative for relative in REQUIRED_PROJECT_FILES if not (repo_root / relative).is_file()]
    if missing:
        return _check(
            "project_files",
            "error",
            "Required project data files are missing",
            details={"missing": ", ".join(missing)},
            remediation="Restore the missing tracked files before running simulations.",
        )
    return _check(
        "project_files",
        "pass",
        "Required project data files are present",
        details={"count": str(len(REQUIRED_PROJECT_FILES))},
    )


def _check_workspace(repo_root: Path) -> dict:
    if not repo_root.is_dir():
        return _check(
            "workspace",
            "error",
            "Repository root does not exist",
            details={"repository": str(repo_root)},
        )
    if not os.access(repo_root, os.W_OK):
        return _check(
            "workspace",
            "error",
            "Repository output directory is not writable",
            details={"repository": str(repo_root)},
            remediation="Choose a writable checkout or adjust its directory permissions.",
        )
    return _check(
        "workspace",
        "pass",
        "Repository output directory is writable",
        details={"repository": str(repo_root)},
    )


def collect_environment_report(
    repo_root: Path,
    *,
    environ: Mapping[str, str] | None = None,
    system_name: str | None = None,
    executable: str | None = None,
) -> dict:
    """Collect a deterministic, timestamp-free environment report."""

    repo_root = repo_root.resolve()
    active_environ = os.environ if environ is None else environ
    active_system = platform.system() if system_name is None else system_name
    active_executable = sys.executable if executable is None else executable

    checks = [_check_python(active_executable)]
    checks.append(
        check_python_command_consistency(
            Path(active_executable),
            python_command=Path(value) if (value := shutil.which("python")) else None,
            python3_command=Path(value) if (value := shutil.which("python3")) else None,
            system_name=active_system,
        )
    )
    checks.extend(_check_distribution(name, version) for name, version in REQUIRED_DISTRIBUTIONS)

    make_check, _ = _check_tool("make", required=True)
    git_check, _ = _check_tool("git", required=True)
    compiler_check, compiler = _check_tool("g++", required=True)
    iverilog_check, _ = _check_tool("iverilog", required=False)
    checks.extend((make_check, git_check, compiler_check))
    checks.append(
        check_cpp_runtime_compatibility(
            compiler,
            path_value=active_environ.get("PATH", ""),
            system_name=active_system,
            executable_dir=repo_root,
        )
    )
    checks.extend((_check_project_files(repo_root), _check_workspace(repo_root), iverilog_check))

    statuses = {item["status"] for item in checks}
    if "error" in statuses:
        overall_status = "error"
    elif "warning" in statuses:
        overall_status = "warning"
    else:
        overall_status = "pass"

    remediation: list[str] = []
    for item in checks:
        action = item.get("remediation")
        if action and action not in remediation:
            remediation.append(action)

    return {
        "schema_version": DOCTOR_SCHEMA_VERSION,
        "overall_status": overall_status,
        "environment": {
            "platform": active_system,
            "python_executable": active_executable,
            "repository": str(repo_root),
        },
        "checks": checks,
        "remediation": remediation,
    }


def format_environment_report(report: Mapping[str, object]) -> str:
    lines = [f"ECC environment doctor: {str(report['overall_status']).upper()}"]
    for raw_check in report["checks"]:  # type: ignore[index]
        check = dict(raw_check)
        lines.append(f"[{check['status'].upper():7}] {check['id']}: {check['summary']}")
        for key, value in check.get("details", {}).items():
            if value:
                lines.append(f"          {key}={value}")
    remediation = report.get("remediation", [])
    if remediation:
        lines.append("Remediation:")
        lines.extend(f"  - {item}" for item in remediation)
    return "\n".join(lines)


def run_environment_doctor(
    repo_root: Path,
    *,
    json_output: bool = False,
    strict: bool = False,
) -> int:
    report = collect_environment_report(repo_root)
    if json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_environment_report(report))
    return 1 if strict and report["overall_status"] == "error" else 0


def doctor_cli(argv: Sequence[str], *, repo_root: Path) -> int:
    parser = argparse.ArgumentParser(
        prog="eccsim.py doctor",
        description="Diagnose the ECC development and simulation environment",
    )
    parser.add_argument("--json", action="store_true", help="Emit the diagnostic report as JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when a required check fails",
    )
    args = parser.parse_args(list(argv))
    return run_environment_doctor(repo_root, json_output=args.json, strict=args.strict)
