import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "golden"


def test_smoke_test_script_stdout_golden():
    result = subprocess.run(
        ["bash", "tests/smoke_test.sh"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == (FIXTURES / "smoke_test.stdout.txt").read_text(encoding="utf-8")
