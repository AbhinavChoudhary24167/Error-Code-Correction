import re
import subprocess
import sys
from pathlib import Path

def test_eccsim_version_prints_three_identifiers():
    script = Path(__file__).resolve().parents[2] / "eccsim.py"
    result = subprocess.run(
        [sys.executable, str(script), "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    output = result.stdout.strip()
    pattern = r"^[0-9a-f]{40} [0-9a-f]{64} .+"
    assert re.match(pattern, output)
