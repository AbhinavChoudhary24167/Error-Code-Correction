# Installation

## Supported environments

Repository continuous integration exercises Ubuntu with Python 3.10, 3.11, and 3.12, and Windows with Python 3.11 plus MSYS2/MinGW. The local documentation rebuild was exercised on Windows with Python 3.12. The portable baseline is therefore Python **3.10–3.12**, GNU Make, Git, and a C++17 compiler. Other systems may work but are not part of the recorded matrix.

Required Python packages come directly from `requirements.txt`: NumPy, SciPy ≥1.11, pandas, pytest, jsonschema, Matplotlib, PyYAML, and scikit-learn 1.7.2.

Optional tools:

| Tool | Use | Absence behavior |
|---|---|---|
| Icarus Verilog | RTL simulation/differential evidence | Relevant RTL test is unavailable or skipped; software adapters can still run |
| Verilator | Optional RTL lint/simulation flows | Tool discovery records unavailable/unreadable; no result is fabricated |
| Yosys | Generic structural synthesis | Structural fields remain unavailable; even when present they are not physical PPA |
| OpenSTA/OpenROAD + SKY130/OpenRAM | Intended open physical flow | Backend manifest remains unavailable and physical fields null |
| Cadence Genus/Innovus/Tempus + ST65 collateral | Intended commercial physical flow | Backend manifest remains unavailable and physical fields null |

No physical-design toolchain is installed automatically.

## Windows PowerShell

Verified interface; package installation depends on local network/package configuration:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python eccsim.py doctor --json
```

For the C++ build, place GNU Make and a C++17 `g++` on `PATH`. If MSYS2/MinGW and another application provide different `libstdc++-6.dll` files, prepend the compiler runtime directory before running native binaries. `doctor` reports this mismatch explicitly.

## Bash, Linux, or WSL

CI-equivalent commands:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python eccsim.py doctor --json
make
python -m pytest -q
```

Distribution package names vary. A typical Ubuntu installation for optional RTL/structural checks is `iverilog verilator yosys`; this is expected from CI but was not installed by the documentation build.

## Verify installation

```text
python eccsim.py --version
python eccsim.py doctor --json
python eccsim.py ecc list
python -m pytest -q tests/python/test_multi_ecc_framework.py
```

Expected discovery concepts, with machine paths omitted:

```json
{
  "checks": [
    {"id": "python", "status": "pass"},
    {"id": "dependency:numpy", "status": "pass"},
    {"id": "tool:make", "status": "pass"},
    {"id": "tool:g++", "status": "pass"},
    {"id": "tool:iverilog", "status": "pass"}
  ],
  "overall_status": "pass_or_environment_specific_error"
}
```

The example is illustrative structure, not a claim that every optional tool is present. The local rebuild found Icarus Verilog and Yosys, but also found a Windows C++ runtime-order mismatch and an unreadable Verilator launcher. Catalogue generation and Python verification remained usable; `doctor --strict` should fail until a required environment error is corrected.
