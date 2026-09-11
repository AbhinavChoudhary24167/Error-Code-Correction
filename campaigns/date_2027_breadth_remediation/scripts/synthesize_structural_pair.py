#!/usr/bin/env python3
"""Run a common mapped-synthesis sanity check for the structural pair."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from collections import defaultdict
from pathlib import Path


IMAGE = "openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
LIBERTY = "/OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
CAMPAIGN = Path("campaigns/date_2027_breadth_remediation")
ENCODER = "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv"
SYNDROME = "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv"
BASELINE_DECODER = "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v2_algorithmic_decoder.sv"
BASELINE_BOUNDARY = "scripts/revision2/rtl/rev2_hsiao_boundary.sv"
NEW_DECODER = f"{CAMPAIGN.as_posix()}/rtl/hsiao_secded_72_64_v3_hierarchical_decoder.sv"
NEW_BOUNDARY = f"{CAMPAIGN.as_posix()}/rtl/breadth_hsiao_hierarchical_boundary.sv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def graph_signature(payload: dict[str, object]) -> str:
    modules = payload["modules"]
    if len(modules) != 1:
        raise ValueError(f"expected one flattened module, found {list(modules)}")
    module = next(iter(modules.values()))
    adjacency: dict[str, list[tuple[str, str]]] = defaultdict(list)
    labels: dict[str, str] = {}

    def connect(left: str, right: str, edge: str) -> None:
        adjacency[left].append((edge, right))
        adjacency[right].append((edge, left))

    for cell_name, cell in module.get("cells", {}).items():
        cell_node = f"cell:{cell_name}"
        labels[cell_node] = f"cell:{cell['type']}"
        directions = cell.get("port_directions", {})
        for port_name, bits in cell.get("connections", {}).items():
            for index, bit in enumerate(bits):
                if isinstance(bit, int):
                    bit_node = f"bit:{bit}"
                    labels.setdefault(bit_node, "net")
                else:
                    bit_node = f"const:{bit}"
                    labels.setdefault(bit_node, f"const:{bit}")
                connect(cell_node, bit_node, f"{directions.get(port_name, '?')}:{port_name}:{index}")

    for port_name, port in module.get("ports", {}).items():
        for index, bit in enumerate(port["bits"]):
            port_node = f"port:{port_name}:{index}"
            labels[port_node] = f"port:{port_name}:{port['direction']}:{index}"
            bit_node = f"bit:{bit}" if isinstance(bit, int) else f"const:{bit}"
            labels.setdefault(bit_node, "net" if isinstance(bit, int) else f"const:{bit}")
            connect(port_node, bit_node, "port")

    colors = {node: hashlib.sha256(label.encode()).hexdigest() for node, label in labels.items()}
    for _ in range(12):
        refined = {}
        for node in sorted(labels):
            neighborhood = sorted((edge, colors[neighbor]) for edge, neighbor in adjacency[node])
            material = json.dumps([labels[node], neighborhood], separators=(",", ":"))
            refined[node] = hashlib.sha256(material.encode()).hexdigest()
        if all(refined[node] == colors[node] for node in colors):
            break
        colors = refined
    cell_colors = sorted(colors[node] for node in labels if node.startswith("cell:"))
    return hashlib.sha256("\n".join(cell_colors).encode()).hexdigest()


def run_one(repo: Path, output: Path, top: str, sources: list[str]) -> dict[str, object]:
    output.mkdir(parents=True)
    source_args = " ".join(f"/repo/{source}" for source in sources)
    yosys_script = (
        f"read_verilog -sv {source_args}; "
        f"hierarchy -check -top {top}; proc; flatten; opt; memory; opt; techmap; opt; "
        f"dfflibmap -liberty {LIBERTY}; abc -liberty {LIBERTY}; clean -purge; "
        "rename -top synthesized_top; "
        f"tee -o /out/stat.json stat -json -liberty {LIBERTY}; "
        "tee -o /out/ltp.log ltp -noff; "
        "write_verilog -noattr /out/mapped_netlist.v; write_json /out/mapped_netlist.json"
    )
    command = [
        "docker", "run", "--rm", "--platform", "linux/amd64",
        "--volume", f"{repo}:/repo:ro",
        "--volume", f"{output}:/out",
        "--entrypoint", "/bin/bash", IMAGE, "-lc",
        f"source /OpenROAD-flow-scripts/env.sh; yosys -p \"{yosys_script}\"",
    ]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=1200,
    )
    runtime = time.monotonic() - started
    (output / "synthesis.log").write_text(completed.stdout, encoding="utf-8", newline="\n")
    (output / "command.txt").write_text(" ".join(command) + "\n", encoding="utf-8", newline="\n")
    if completed.returncode != 0:
        raise SystemExit(f"common-policy synthesis failed for {top}; see {output / 'synthesis.log'}")

    stat = json.loads((output / "stat.json").read_text(encoding="utf-8"))
    netlist = json.loads((output / "mapped_netlist.json").read_text(encoding="utf-8"))
    module_stats = stat["modules"]["\\synthesized_top"]
    histogram = {key.lstrip("\\"): int(value) for key, value in module_stats.get("num_cells_by_type", {}).items()}
    ltp_text = (output / "ltp.log").read_text(encoding="utf-8")
    depth_match = re.search(r"Longest topological path in .* length (\d+)", ltp_text)

    def count_type(*tokens: str) -> int:
        return sum(count for cell, count in histogram.items() if any(token in cell.lower() for token in tokens))

    return {
        "top": top,
        "sources": [{"path": source, "sha256": sha256(repo / source)} for source in sources],
        "yosys_script": yosys_script,
        "runtime_seconds": runtime,
        "mapped_cell_count": int(module_stats["num_cells"]),
        "wire_count": int(module_stats["num_wires"]),
        "wire_bit_count": int(module_stats["num_wire_bits"]),
        "public_wire_count": int(module_stats["num_pub_wires"]),
        "memory_count": int(module_stats["num_memories"]),
        "process_count": int(module_stats["num_processes"]),
        "cell_type_histogram": histogram,
        "xor_xnor_count": count_type("xor", "xnor"),
        "mux_count": count_type("mux"),
        "register_count": count_type("df", "dlatch"),
        "logic_depth_no_flip_flops": int(depth_match.group(1)) if depth_match else None,
        "mapped_netlist_sha256": sha256(output / "mapped_netlist.v"),
        "mapped_json_sha256": sha256(output / "mapped_netlist.json"),
        "name_independent_graph_signature": graph_signature(netlist),
        "synthesis_log_sha256": sha256(output / "synthesis.log"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    formal = json.loads((repo / CAMPAIGN / "formal/results/A_formal_qualification.json").read_text(encoding="utf-8"))
    if formal["formal_status"] != "PASS" or not formal["physical_authorized"]:
        raise SystemExit("structural-pair formal gate is not PASS")
    root = repo / CAMPAIGN / "synthesis"
    if root.exists():
        raise SystemExit(f"refusing to overwrite structural synthesis evidence: {root}")

    common = [ENCODER, SYNDROME]
    baseline = run_one(
        repo,
        root / "baseline_flat",
        "gate04_rev2_hsiao_72_64",
        common + [BASELINE_DECODER, BASELINE_BOUNDARY],
    )
    hierarchical = run_one(
        repo,
        root / "new_hierarchical",
        "breadth_hsiao_hierarchical_72_64",
        common + [NEW_DECODER, NEW_BOUNDARY],
    )
    distinct = (
        baseline["name_independent_graph_signature"] != hierarchical["name_independent_graph_signature"]
        or baseline["cell_type_histogram"] != hierarchical["cell_type_histogram"]
    )
    payload = {
        "schema_version": 1,
        "status": "PASS" if distinct else "FAIL",
        "criterion": "mapped cell histogram or name-independent mapped graph signature differs under one common synthesis policy",
        "container_image": IMAGE,
        "liberty": LIBERTY,
        "baseline": baseline,
        "new_hierarchical": hierarchical,
        "differences": {
            "mapped_cell_count": hierarchical["mapped_cell_count"] - baseline["mapped_cell_count"],
            "register_count": hierarchical["register_count"] - baseline["register_count"],
            "xor_xnor_count": hierarchical["xor_xnor_count"] - baseline["xor_xnor_count"],
            "mux_count": hierarchical["mux_count"] - baseline["mux_count"],
            "logic_depth_no_flip_flops": (
                None
                if baseline["logic_depth_no_flip_flops"] is None or hierarchical["logic_depth_no_flip_flops"] is None
                else hierarchical["logic_depth_no_flip_flops"] - baseline["logic_depth_no_flip_flops"]
            ),
            "cell_type_histogram_equal": baseline["cell_type_histogram"] == hierarchical["cell_type_histogram"],
            "name_independent_graph_signature_equal": (
                baseline["name_independent_graph_signature"] == hierarchical["name_independent_graph_signature"]
            ),
        },
    }
    write_json(root / "A_synthesis_structural_comparison.json", payload)
    print(f"G3_STRUCTURAL_PAIR_SYNTHESIS_DISTINCTNESS = {payload['status']}")
    return 0 if distinct else 1


if __name__ == "__main__":
    raise SystemExit(main())
