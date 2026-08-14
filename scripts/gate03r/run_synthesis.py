#!/usr/bin/env python3
"""Run Gate 03R generic synthesis and name-independent structure checks."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "date2027" / "rigour_gate_03r"
OUT = DOC / "baseline" / "generic_synthesis"
CHAR = "scripts/gate03r/rtl/secded_characterization_tops.sv"
PIPE = "asic/rtl/secded/secded_pipelined_72_64_v1.sv"
BCH = "asic/rtl/bch/bch_78_64_t2_v1.sv"

JOBS = [
    ("gate03r_secded_baseline_encoder", [CHAR]),
    ("gate03r_secded_baseline_decoder", [CHAR]),
    ("gate03r_secded_baseline_combined", [CHAR]),
    ("secded_pipelined_72_64_v1_encoder", [PIPE]),
    ("secded_pipelined_72_64_v1_decoder", [PIPE]),
    ("gate03r_secded_pipelined_combined", [PIPE, CHAR]),
    ("bch_78_64_t2_v1_encoder", [BCH]),
    ("bch_78_64_t2_v1_decoder", [BCH]),
]


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def structure(netlist: dict[str, Any], top: str) -> dict[str, Any]:
    module = netlist["modules"][top]
    cells = module.get("cells", {})
    cell_types = Counter(str(cell["type"]) for cell in cells.values())
    dff_count = sum(count for kind, count in cell_types.items() if "DFF" in kind.upper())
    ports = {
        name: {"direction": item["direction"], "width": len(item["bits"])}
        for name, item in module.get("ports", {}).items()
    }
    # A compact name-independent signature: cell type/parameter/port-width
    # records plus the module boundary.  Sequential-vs-combinational identity
    # is independently guarded by the DFF count.
    cell_records = []
    for cell in cells.values():
        connections = cell.get("connections", {})
        cell_records.append(
            {
                "type": cell["type"],
                "parameters": cell.get("parameters", {}),
                "ports": sorted((name, len(bits)) for name, bits in connections.items()),
                "directions": cell.get("port_directions", {}),
            }
        )
    normalized = {
        "ports": ports,
        "cell_records": sorted(cell_records, key=lambda item: json.dumps(item, sort_keys=True)),
        "cell_type_counts": dict(sorted(cell_types.items())),
        "memory_count": len(module.get("memories", {})),
    }
    return {
        "normalized_graph_sha256": canonical_hash(normalized),
        "cell_count": len(cells),
        "dff_count": dff_count,
        "cell_type_counts": dict(sorted(cell_types.items())),
        "port_contract": ports,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    yosys = shutil.which("yosys") or str(Path(r"D:\Compiler Cpp\ucrt64\bin\yosys.exe"))
    results: dict[str, Any] = {}
    for top, sources in JOBS:
        json_path = OUT / f"{top}.json"
        verilog_path = OUT / f"{top}.v"
        script = (
            f"read_verilog -sv {' '.join(sources)}; hierarchy -check -top {top}; "
            f"proc; flatten; opt; synth -top {top} -flatten; check; "
            f"write_json {json_path.relative_to(ROOT).as_posix()}; "
            f"write_verilog -noattr {verilog_path.relative_to(ROOT).as_posix()}"
        )
        command = [yosys, "-p", script]
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                check=False,
            )
            exit_code = completed.returncode
            transcript = completed.stdout + completed.stderr
            status = "PASS" if exit_code == 0 and json_path.is_file() else "FAIL"
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            transcript = (exc.stdout or "") + (exc.stderr or "") + "\nTIMEOUT_AFTER_120_SECONDS\n"
            status = "TIMEOUT"
        (OUT / f"{top}.log").write_text(
            "$ " + subprocess.list2cmdline(command) + "\n" + transcript + f"\nexit_code={exit_code}\n",
            encoding="utf-8",
            newline="\n",
        )
        result: dict[str, Any] = {"status": status, "exit_code": exit_code, "sources": sources}
        if status == "PASS":
            result.update(structure(json.loads(json_path.read_text(encoding="utf-8")), top))
        results[top] = result

    baseline_encoder = results["gate03r_secded_baseline_encoder"]
    pipeline_encoder = results["secded_pipelined_72_64_v1_encoder"]
    baseline_decoder = results["gate03r_secded_baseline_decoder"]
    pipeline_decoder = results["secded_pipelined_72_64_v1_decoder"]
    comparisons = {
        "encoder_generic_graphs_distinct": (
            baseline_encoder.get("normalized_graph_sha256")
            != pipeline_encoder.get("normalized_graph_sha256")
        ),
        "decoder_generic_graphs_distinct": (
            baseline_decoder.get("normalized_graph_sha256")
            != pipeline_decoder.get("normalized_graph_sha256")
        ),
        "baseline_encoder_has_no_dff": baseline_encoder.get("dff_count") == 0,
        "baseline_decoder_has_no_dff": baseline_decoder.get("dff_count") == 0,
        "pipeline_encoder_has_dff": int(pipeline_encoder.get("dff_count", 0)) > 0,
        "pipeline_decoder_has_dff": int(pipeline_decoder.get("dff_count", 0)) > 0,
    }
    payload = {
        "schema_version": 1,
        "classification": "GENERIC_SYNTHESIS_ONLY_NOT_PPA",
        "jobs": results,
        "h2_generic_structure_comparison": comparisons,
        "h2_generic_status": "PASS" if all(comparisons.values()) else "FAIL",
        "sky130hd_mapping": {
            "status": "BLOCKED_PINNED_ORFS_ENVIRONMENT_UNAVAILABLE",
            "claims_generated": False,
        },
    }
    (DOC / "SYNTHESIS_AND_STRUCTURE_RESULTS.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({"jobs": {k: v["status"] for k, v in results.items()}, "h2": payload["h2_generic_status"]}, indent=2))
    return 0 if all(item["status"] == "PASS" for item in results.values()) and all(comparisons.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
