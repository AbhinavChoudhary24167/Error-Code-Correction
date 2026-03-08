import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "golden"


def test_smoke_test_script_stdout_golden():
    result = subprocess.run(
        [sys.executable, "tests/smoke_test.py"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == (FIXTURES / "smoke_test.stdout.txt").read_text(encoding="utf-8")
