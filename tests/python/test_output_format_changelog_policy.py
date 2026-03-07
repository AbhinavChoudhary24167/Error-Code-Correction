import os
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
APPROVALS = REPO / "docs" / "output_format_approvals.md"

TRACKED_OUTPUT_FILES = {
    "tests/fixtures/golden/select.stdout.txt",
    "tests/fixtures/golden/target.stdout.txt",
    "tests/fixtures/golden/ecc_selector_legacy.stdout.txt",
    "tests/fixtures/golden/ecc_selector_legacy.stderr.txt",
    "tests/fixtures/golden/reliability_report.json",
    "tests/fixtures/golden/select_candidates.csv",
    "tests/fixtures/golden/select_pareto.csv",
    "tests/fixtures/golden/target_choice.json",
    "tests/fixtures/golden/target_feasible.csv",
    "tests/fixtures/golden/energy_default.stdout.txt",
    "tests/fixtures/golden/carbon_default.stdout.txt",
    "tests/fixtures/golden/hazucha_default.stdout.txt",
    "tests/fixtures/golden/esii_default.json",
    "tests/fixtures/golden/smoke_test.stdout.txt",
}


def _changed_files_against_base() -> set[str]:
    base_ref_candidates = []
    github_base = os.environ.get("GITHUB_BASE_REF")
    if github_base:
        base_ref_candidates.append(f"origin/{github_base}")
    base_ref_candidates.extend(["origin/main", "origin/master", "HEAD~1"])

    for candidate in base_ref_candidates:
        merge_base = subprocess.run(
            ["git", "merge-base", "HEAD", candidate],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        if merge_base.returncode != 0:
            continue
        base = merge_base.stdout.strip()
        if not base:
            continue
        diff = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        )
        return {line.strip() for line in diff.stdout.splitlines() if line.strip()}

    return set()


def test_output_format_changes_require_changelog_approval():
    changed_files = _changed_files_against_base()
    changed_tracked = sorted(TRACKED_OUTPUT_FILES.intersection(changed_files))
    if not changed_tracked:
        return

    assert APPROVALS.is_file(), (
        "Default output fixtures changed but docs/output_format_approvals.md is missing. "
        "Add an explicit approval entry before merging."
    )

    approvals = APPROVALS.read_text(encoding="utf-8")
    for changed_file in changed_tracked:
        token = f"APPROVED-OUTPUT-FORMAT-CHANGE: {changed_file}"
        assert token in approvals, (
            "Default output format changed without explicit approval for "
            f"{changed_file}. Add '{token}' to docs/output_format_approvals.md."
        )
