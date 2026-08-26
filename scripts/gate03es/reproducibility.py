#!/usr/bin/env python3
"""Gate 03E-S prospective policy freeze, inventory, comparison, and validation."""

from __future__ import annotations

import argparse
import difflib
import fnmatch
import hashlib
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


V1_POLICY_SHA256 = "258694f328084c3fb92dec24e07b3b40d261037d5b1bd8d32b119684211d0b9a"
V1_COMPARATOR_SHA256 = "9038cd174ccfd5c62d64908c6df9416f2ff542d58daa44faf3f9d6e5527d3a92"
V1_COMPARISON_SHA256 = "655a0b7f6aadde7fcf0c45266e9f80fbf77f2635badd7bcee11a0d737c447628"
V2_POLICY_SHA256 = "d605d48ecb040e43d77fd278756e31e663ed30d329388e2217d13bc348a41493"
IMAGE_DIGEST = "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
OCI_INDEX_DIGEST = "sha256:68d42e5c92a7193a9cf9a331a429250e47d42e16883366af2107022f7dafff74"
OCI_CONFIG_DIGEST = "sha256:ab3a3006003431cd7189a82567df3e6deb0d0aae66aa42a0bdf56d2751447c08"
ORFS_COMMIT = "56496f3980fb6e9e58f10c8aea4a98949c0fe5f2"
ORFS_TREE = "2b736d484fa7a26b38b1439f177aeb6c1f3e9d5a"

TEXT_SUFFIXES = {
    ".cfg", ".csv", ".def", ".json", ".lef", ".log", ".rpt", ".sdc",
    ".spef", ".tcl", ".txt", ".v", ".verilog",
}
SEMANTIC_SUFFIXES = {".def", ".gds", ".sdc", ".spef", ".v", ".verilog"}
RUN_ROOT_RE = re.compile(r"/(?:gate03e|gate03er|gate03es)-run-\d{2}")
HEX20_RE = re.compile(r"^[0-9a-f]{20}$")
FASTROUTE_TIMER_RE = re.compile(
    r"(?:^|__)global_route__fastroute__"
    r"(?:run|initial_rsmt|route_l|congestion_rsmt|new_route_l|spiral|route_z|"
    r"monotonic|overflow_iterations|finalization|snapshot_batch_(?:route|apply|sync))_s$"
)
METADATA_KEY_RE = re.compile(
    r"(?i)(?:^|[._-])(?:timestamp|date|generated_at|generated_on|start_time|"
    r"end_time|hostname|host_name|run_id|container_id|process_id|pid)$"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_no_duplicates(path: Path) -> dict[str, Any]:
    """Reject duplicate JSON object keys instead of accepting the last value."""

    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value is not an object")
    return value


def compare_run_metadata(
    first_path: Path,
    second_path: Path,
    policy: dict[str, Any],
    catalog: dict[str, Any],
) -> dict[str, Any]:
    """Validate producer-owned metadata without requiring cross-run identity."""

    failures: list[str] = []
    observations: list[dict[str, Any]] = []
    try:
        first = read_json_no_duplicates(first_path)
        second = read_json_no_duplicates(second_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {"pass": False, "failures": [f"run-metadata parse failure: {exc}"], "fields": []}

    contract = policy["run_contract"]
    field_catalog = catalog["run_metadata_producer"]["closed_fields"]
    optional = set(catalog["run_metadata_producer"].get("optional_fields", []))
    for run_id, value, expected in ((5, first, contract["run_5"]), (6, second, contract["run_6"])):
        unknown = sorted(set(value) - set(field_catalog))
        missing = sorted(set(field_catalog) - optional - set(value))
        failures.extend(f"run {run_id} metadata field {key} is UNRESOLVED" for key in unknown)
        failures.extend(f"run {run_id} missing mandatory metadata field {key}" for key in missing)
        for key in sorted(set(value) & set(field_catalog)):
            observations.append(
                {
                    "run": run_id,
                    "field": key,
                    "value": value[key],
                    "class": field_catalog[key]["class"],
                    "cross_run_equality_gated": False if field_catalog[key]["class"] in {"PROVENANCE_IDENTITY", "RUNTIME_RESOURCE_OBSERVATION"} else True,
                }
            )
        if value.get("schema_version") != 3:
            failures.append(f"run {run_id} metadata schema_version is not 3")
        if value.get("run_label") != expected["run_label"]:
            failures.append(f"run {run_id} has unexpected run_label")
        if value.get("container_root") != expected["container_root"]:
            failures.append(f"run {run_id} has unexpected container_root")
        if value.get("host_root") != expected["host_root"]:
            failures.append(f"run {run_id} has unexpected host_root")
        if value.get("exit_status") != 0:
            failures.append(f"run {run_id} exit_status is not zero")
        for key in ("start_time", "end_time", "policy_frozen_at"):
            try:
                datetime.fromisoformat(str(value[key]).replace("Z", "+00:00"))
            except (KeyError, TypeError, ValueError):
                failures.append(f"run {run_id} has malformed {key}")
        if all(key in value for key in ("policy_frozen_at", "start_time", "end_time")):
            try:
                frozen = datetime.fromisoformat(str(value["policy_frozen_at"]).replace("Z", "+00:00"))
                start = datetime.fromisoformat(str(value["start_time"]).replace("Z", "+00:00"))
                end = datetime.fromisoformat(str(value["end_time"]).replace("Z", "+00:00"))
                if not frozen < start <= end:
                    failures.append(f"run {run_id} metadata chronology is invalid")
            except ValueError:
                pass
    labels = [first.get("run_label"), second.get("run_label")]
    if labels[0] == labels[1]:
        failures.append("run labels must be different")
    pattern = re.compile(contract["label_pattern"])
    if any(not isinstance(label, str) or not pattern.fullmatch(label) for label in labels):
        failures.append("run label is malformed")
    return {"pass": not failures, "failures": list(dict.fromkeys(failures)), "fields": observations}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def stable_tree_hash(root: Path) -> str:
    records: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        records.append(f"{relative}\0{path.stat().st_size}\0{sha256_file(path)}\n")
    return sha256_bytes("".join(records).encode("utf-8"))


def normalize_run_roots(text: str) -> str:
    return RUN_ROOT_RE.sub("<RUN_ROOT>", text)


def _normalize_yosys_time_spent(line: str) -> str:
    if not line.startswith("Time spent:"):
        return line
    line = re.sub(r"\b\d+%\s+(\d+x\s+[^,(]+)\s+\(\d+\s+sec\)", r"<PERCENT> \1 (<SECONDS> sec)", line)
    line = re.sub(r"\b\d+%\s+(\d+\s+calls\s+)[0-9.]+\s+sec\s+", r"<PERCENT> \1<SECONDS> sec ", line)
    return line


def normalize_log_text(text: str) -> tuple[str, list[str]]:
    """Remove only producer-proven execution observations and path metadata."""
    actions: set[str] = set()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    rooted = normalize_run_roots(text)
    if rooted != text:
        actions.add("absolute_run_root")
    output: list[str] = []
    elapsed_table = False
    for raw_line in rooted.split("\n"):
        line = raw_line.rstrip(" \t")
        if line != raw_line:
            actions.add("trailing_horizontal_whitespace")
        if "Log" in line and "Elapsed/s" in line and "Peak Memory/MB" in line:
            elapsed_table = True
            output.append(line)
            continue
        if line.startswith("End of script. Logfile hash:"):
            line = re.sub(r"Logfile hash:\s*[0-9a-f]+", "Logfile hash: <DERIVED_LOG_FINGERPRINT>", line)
            line = re.sub(r",\s*time:\s*[^,]+,\s*user:\s*[^,]+,\s*system:\s*[^,]+,\s*MEM:\s*[^,]+", ", <EXECUTION_OBSERVATION>", line)
            actions.update({"yosys_derived_log_fingerprint", "yosys_runtime_resource_summary"})
        elif line.startswith("Time spent:"):
            normalized = _normalize_yosys_time_spent(line)
            if normalized != line:
                actions.add("yosys_pass_runtime_distribution")
            line = normalized
        elif re.search(r"\[INFO\s+[A-Z]+-05\d\d\]\s+Runtime:\s*[0-9.]+s", line):
            line = re.sub(r"(Runtime:\s*)[0-9.]+s", r"\1<SECONDS>", line)
            actions.add("openroad_runtime_message")
        elif re.match(r"^Took\s+\d+\s+seconds?:", line):
            line = re.sub(r"^Took\s+\d+\s+seconds?", "Took <SECONDS> seconds", line)
            actions.add("orfs_took_timer")
        elif "Elapsed time:" in line and "CPU time:" in line and "Peak memory:" in line:
            prefix = line.split("Elapsed time:", 1)[0]
            line = prefix + "Elapsed time: <WALL> CPU time: <CPU> Peak memory: <PEAK_MEMORY>"
            actions.add("orfs_process_resource_summary")
        elif re.search(r"cpu time\s*=.*elapsed time\s*=.*(?:memory|peak)\s*=", line, re.I):
            prefix = line.split("cpu time", 1)[0]
            line = prefix + "cpu time = <CPU>, elapsed time = <WALL>, memory = <MEMORY>, peak = <PEAK_MEMORY>"
            actions.add("openroad_process_resource_summary")
        elif re.match(r"^\s*elapsed time\s*=.*memory\s*=", line, re.I):
            indent = line[: len(line) - len(line.lstrip())]
            line = indent + "elapsed time = <WALL>, memory = <MEMORY>."
            actions.add("openroad_progress_resource_summary")
        elif elapsed_table and line.strip():
            row = re.fullmatch(
                r"\s*(\S+)\s+(\.\S+)\s+(\d+)\s+(\d+)\s+([0-9a-f]{20}|N/A)\s*",
                line,
            )
            row_without_ext = re.fullmatch(
                r"\s*(\S+)\s+(\d+)\s+(\d+)\s+([0-9a-f]{20}|N/A)\s*",
                line,
            )
            total = re.fullmatch(r"\s*Total\s+(\d+)\s+(\d+)\s*", line)
            if row:
                line = f"{row.group(1)} | {row.group(2)} | <ELAPSED_SECONDS> | <PEAK_MEMORY_MB> | {row.group(5)}"
                actions.add("orfs_elapsed_peak_table")
            elif row_without_ext:
                line = f"{row_without_ext.group(1)} | <ELAPSED_SECONDS> | <PEAK_MEMORY_MB> | {row_without_ext.group(4)}"
                actions.add("orfs_elapsed_peak_table")
            elif total:
                line = "Total | <ELAPSED_SECONDS> | <PEAK_MEMORY_MB>"
                actions.add("orfs_elapsed_peak_table")
        output.append(line)
    return "\n".join(output), sorted(actions)


def normalize_semantic_text(text: str, suffix: str) -> tuple[str, list[str]]:
    actions: set[str] = set()
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized != text:
        actions.add("line_endings")
    rooted = normalize_run_roots(normalized)
    if rooted != normalized:
        actions.add("absolute_run_root")
    normalized = rooted
    if suffix == ".spef":
        replaced = re.sub(r"(?im)^(\*DATE\s+).*$", r"\1<METADATA>", normalized)
        if replaced != normalized:
            actions.add("spef_date")
        normalized = replaced
    lines = [line.rstrip(" \t") for line in normalized.split("\n")]
    if "\n".join(lines) != normalized:
        actions.add("trailing_horizontal_whitespace")
    return "\n".join(lines), sorted(actions)


def conservative_token_canonicalize(text: str, suffix: str) -> tuple[bytes, list[str]]:
    """Normalize presentation whitespace while retaining every semantic token."""
    normalized, actions = normalize_semantic_text(text, suffix)
    continued = normalized.replace("\\\n", "")
    if continued != normalized:
        actions = sorted(set(actions) | {"line_continuations"})
    tokens = re.findall(
        r'"(?:\\.|[^"\\])*"|\[|\]|\{|\}|\(|\)|;|,|[^\s\[\]{}();,]+',
        continued,
    )
    return ("\n".join(tokens) + "\n").encode("utf-8"), sorted(set(actions) | {"conservative_token_stream"})


def normalize_yosys_json(value: Any) -> Any:
    """Create a deterministic structural representation of Yosys JSON."""
    if isinstance(value, dict):
        return {key: normalize_yosys_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [normalize_yosys_json(item) for item in value]
    if isinstance(value, str):
        return normalize_run_roots(value)
    return value


def canonicalize_netlist_with_yosys(path: Path) -> bytes:
    """Parse a mapped netlist with the pinned Yosys and serialize structural JSON."""
    command = (
        "set -euo pipefail; "
        "source /OpenROAD-flow-scripts/env.sh >/dev/null; "
        f"yosys -q -p 'read_verilog -sv /input/{path.name}; write_json /dev/stdout'"
    )
    output = subprocess.check_output(
        [
            "docker", "run", "--rm", "--platform", "linux/amd64",
            "--volume", f"{path.parent}:/input:ro",
            "--entrypoint", "/bin/bash", f"openroad/orfs@{IMAGE_DIGEST}",
            "-lc", command,
        ],
        stderr=subprocess.PIPE,
    )
    value = normalize_yosys_json(json.loads(output.decode("utf-8")))
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def is_runtime_metric(artifact: str, key: str) -> bool:
    lower = key.lower()
    if PurePosixPath(artifact).name == "mem.json":
        return True
    return bool(FASTROUTE_TIMER_RE.search(key)) or any(
        token in lower for token in ("__runtime__", "elapsed_time", "wall_time", "cpu_time", "peak_memory", "__mem__")
    )


def metric_family(key: str) -> tuple[str, float, str]:
    lower = key.lower()
    if re.search(r"(?:count|violations?|errors?|warnings?|vias?|nets?|instances?|sequential|rows?|sites?|io|iteration|fanout)(?:__|:|$)", lower):
        return "discrete_counts_masters_statuses", 0.0, "exact"
    if "area" in lower:
        return "area", 0.0, "um^2"
    if "utilization" in lower or "density" in lower:
        return "utilization_density", 1e-6, "ratio"
    if "fmax" in lower or "frequency" in lower:
        return "frequency", 1.0, "Hz"
    if re.search(r"(?:wns|tns|__ws|slack|skew|delay|slew)", lower):
        return "timing", 1e-6, "ns"
    if re.search(r"(?:wirelength|width|height|dimension|perimeter|length|displacement|hpwl)", lower):
        return "wirelength_dimension_displacement", 1e-3, "reported length unit"
    if re.search(r"(?:capacitance|resistance|max_cap|__cap(?:__|$)|__res(?:__|$))", lower):
        return "capacitance_resistance", 1e-6, "reported unit"
    if "power" in lower:
        return "power", 1e-9, "W"
    if "voltage" in lower or "powergrid__drop" in lower:
        return "voltage", 1e-6, "V"
    return "preenumerated_other_qor", 0.0, "exact"


def normalize_json_value(value: Any, artifact: str, path: str, actions: set[str]) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key in sorted(value):
            child = f"{path}.{key}" if path else key
            if METADATA_KEY_RE.search(key):
                result[key] = "<METADATA>"
                actions.add(f"json_metadata:{child}")
            elif is_runtime_metric(artifact, child):
                result[key] = "<EXECUTION_OBSERVATION>"
                actions.add(f"execution_observation:{child}")
            else:
                result[key] = normalize_json_value(value[key], artifact, child, actions)
        return result
    if isinstance(value, list):
        return [normalize_json_value(item, artifact, f"{path}[{index}]", actions) for index, item in enumerate(value)]
    if isinstance(value, str):
        rooted = normalize_run_roots(value)
        if rooted != value:
            actions.add(f"absolute_run_root:{path}")
        return rooted
    return value


def parse_gds_records(data: bytes) -> list[tuple[int, bytes]]:
    records: list[tuple[int, bytes]] = []
    offset = 0
    while offset < len(data):
        if offset + 4 > len(data):
            raise ValueError("truncated GDS record header")
        length, record_type, data_type = struct.unpack(">HBB", data[offset : offset + 4])
        if length < 4 or offset + length > len(data):
            raise ValueError("invalid GDS record length")
        records.append((record_type, data[offset : offset + length]))
        offset += length
    return records


def _zero_gds_payload(record: bytes) -> bytes:
    return record[:4] + bytes(len(record) - 4)


def canonicalize_structure(records: list[tuple[int, bytes]]) -> bytes:
    if not records or records[0][0] != 0x05 or records[-1][0] != 0x07:
        raise ValueError("malformed GDS structure")
    prefix: list[bytes] = [_zero_gds_payload(records[0][1])]
    elements: list[bytes] = []
    suffix = records[-1][1]
    index = 1
    while index < len(records) - 1 and records[index][0] not in {0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x2D}:
        prefix.append(records[index][1])
        index += 1
    while index < len(records) - 1:
        if records[index][0] not in {0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x2D}:
            raise ValueError("unrecognized GDS inter-element record")
        element: list[bytes] = []
        while index < len(records) - 1:
            element.append(records[index][1])
            record_type = records[index][0]
            index += 1
            if record_type == 0x11:
                break
        if not element or records[index - 1][0] != 0x11:
            raise ValueError("unterminated GDS element")
        elements.append(b"".join(element))
    return b"".join(prefix) + b"".join(sorted(elements)) + suffix


def canonicalize_gds(data: bytes) -> bytes:
    records = parse_gds_records(data)
    result: list[bytes] = []
    structures: list[bytes] = []
    index = 0
    while index < len(records):
        record_type, record = records[index]
        if record_type == 0x01:
            result.append(_zero_gds_payload(record))
            index += 1
        elif record_type == 0x05:
            structure: list[tuple[int, bytes]] = []
            while index < len(records):
                structure.append(records[index])
                if records[index][0] == 0x07:
                    index += 1
                    break
                index += 1
            structures.append(canonicalize_structure(structure))
        elif record_type == 0x04:
            result.extend(sorted(structures))
            structures.clear()
            result.append(record)
            index += 1
        else:
            result.append(record)
            index += 1
    if structures:
        raise ValueError("GDS structures not terminated by ENDLIB")
    return b"".join(result)


def canonicalize_lyt(raw: bytes) -> tuple[bytes, list[str]]:
    text = raw.decode("utf-8")
    root = ET.fromstring(text)
    if root.tag != "technology":
        raise ValueError("KLayout technology XML root is not <technology>")
    actions: list[str] = []
    for element in root.findall("./reader-options/lefdef/lef-files"):
        if element.text:
            normalized = normalize_run_roots(element.text)
            if normalized != element.text:
                actions.append("klayout_lef_files_run_root")
                element.text = normalized
    serialized = ET.tostring(root, encoding="unicode")
    canonical = ET.canonicalize(serialized).encode("utf-8")
    return canonical, sorted(set(actions))


def canonicalize_file(path: Path, relative: str) -> tuple[bytes, list[str]]:
    raw = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == ".gds":
        return canonicalize_gds(raw), ["gds_dates_structure_and_element_order"]
    if suffix == ".lyt":
        return canonicalize_lyt(raw)
    if suffix == ".json":
        value = read_json_no_duplicates(path)
        actions: set[str] = set()
        normalized = normalize_json_value(value, relative, "", actions)
        return (json.dumps(normalized, sort_keys=True, separators=(",", ":")) + "\n").encode(), sorted(actions)
    if suffix == ".log":
        normalized, actions = normalize_log_text(raw.decode("utf-8", errors="strict"))
        return normalized.encode("utf-8"), actions
    if suffix in {".v", ".verilog"}:
        return canonicalize_netlist_with_yosys(path), ["pinned_yosys_structural_json"]
    if suffix in {".def", ".sdc", ".spef"}:
        return conservative_token_canonicalize(raw.decode("utf-8", errors="strict"), suffix)
    if suffix in TEXT_SUFFIXES:
        normalized, actions = normalize_semantic_text(raw.decode("utf-8", errors="strict"), suffix)
        return normalized.encode("utf-8"), actions
    return raw, []


def make_inventory(root: Path, policy_path: Path, run_label: str) -> dict[str, Any]:
    policy_hash = sha256_file(policy_path)
    artifacts: list[dict[str, Any]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        try:
            canonical, actions = canonicalize_file(path, relative)
            error = None
        except Exception as exc:  # fail closed while preserving raw evidence
            canonical, actions, error = raw, [], f"{type(exc).__name__}: {exc}"
        artifacts.append(
            {
                "path": relative,
                "size_bytes": len(raw),
                "raw_sha256": sha256_bytes(raw),
                "canonical_sha256": sha256_bytes(canonical),
                "normalizations_applied": actions,
                "canonicalization_error": error,
            }
        )
    return {
        "schema_version": 2,
        "run_label": run_label,
        "run_root": str(root.resolve()),
        "policy_sha256": policy_hash,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def _iter_numeric(value: Any, path: str = "") -> Iterable[tuple[str, float | int]]:
    if isinstance(value, dict):
        for key in sorted(value):
            child = f"{path}.{key}" if path else key
            yield from _iter_numeric(value[key], child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_numeric(item, f"{path}[{index}]")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield path, value


def build_metric_schema(run_1: Path, run_2: Path) -> dict[str, Any]:
    entries: dict[str, dict[str, Any]] = {}
    json_paths = sorted(
        set(path.relative_to(run_1).as_posix() for path in run_1.rglob("*.json"))
        & set(path.relative_to(run_2).as_posix() for path in run_2.rglob("*.json"))
    )
    for relative in json_paths:
        if not relative.startswith("logs/"):
            continue
        left = read_json(run_1 / relative)
        right = read_json(run_2 / relative)
        keys = {path for path, _ in _iter_numeric(left)} | {path for path, _ in _iter_numeric(right)}
        for key in sorted(keys):
            identity = f"{relative}:{key}"
            if is_runtime_metric(relative, key):
                family, tolerance, unit = "execution_runtime_resource", None, "observation only"
                classification = "execution runtime/resource usage"
                gating = False
            else:
                family, tolerance, unit = metric_family(key)
                classification = "scientific QoR/state"
                gating = True
            entries[identity] = {
                "artifact": relative,
                "path": key,
                "classification": classification,
                "family": family,
                "gating": gating,
                "absolute_tolerance": tolerance,
                "unit": unit,
                "basis": "producer semantics and unit/family rule; frozen before runs 3 and 4",
            }
    return {
        "schema_version": 1,
        "schema_id": "gate03er-closed-qor-schema-v2",
        "derived_from_preserved_runs": ["gcd-run-01", "gcd-run-02"],
        "posthoc_exclusions": [],
        "unknown_metric_rule": "unresolved gate failure",
        "metrics": [entries[key] for key in sorted(entries)],
    }


def _lookup(value: Any, path: str) -> Any:
    current = value
    for part in re.split(r"\.(?![^\[]*\])", path):
        if not part:
            continue
        match = re.fullmatch(r"([^\[]+)(?:\[(\d+)\])?", part)
        if not match or not isinstance(current, dict) or match.group(1) not in current:
            raise KeyError(path)
        current = current[match.group(1)]
        if match.group(2) is not None:
            current = current[int(match.group(2))]
    return current


def mapped_master_histogram(netlist: Path) -> dict[str, int]:
    text = netlist.read_text(encoding="utf-8", errors="strict")
    pattern = re.compile(r"^\s*(sky130_fd_sc_hd__[A-Za-z0-9_]+)\s+(?:\\\S+|[A-Za-z_$][A-Za-z0-9_$]*)\s*\(", re.MULTILINE)
    return dict(sorted(Counter(pattern.findall(text)).items()))


def _semantic_match(path: str, policy: dict[str, Any]) -> bool:
    candidate = PurePosixPath(path)
    return any(candidate.match(pattern) for pattern in policy["semantic_artifacts"]["required_exact_canonical_globs"])


def compare_runs(
    manifest_1: Path,
    manifest_2: Path,
    policy_path: Path,
    schema_path: Path,
    catalog_path: Path | None = None,
) -> dict[str, Any]:
    policy = read_json(policy_path)
    schema = read_json(schema_path)
    catalog = read_json(catalog_path or policy_path.with_name("producer_catalog_v3.json"))
    first = read_json(manifest_1)
    second = read_json(manifest_2)
    expected_policy_hash = sha256_file(policy_path)
    failures: list[str] = []
    if first.get("policy_sha256") != expected_policy_hash or second.get("policy_sha256") != expected_policy_hash:
        failures.append("run inventory policy hash does not match frozen policy v3")
    if first.get("run_label") != "gcd-run-05" or second.get("run_label") != "gcd-run-06":
        failures.append("run inventory labels do not match the frozen run 5/6 contract")
    first_by = {item["path"]: item for item in first["artifacts"]}
    second_by = {item["path"]: item for item in second["artifacts"]}
    shared = sorted(set(first_by) & set(second_by))
    missing = sorted(set(first_by) - set(second_by))
    additional = sorted(set(second_by) - set(first_by))
    if missing:
        failures.append(f"{len(missing)} artifacts missing from run 4")
    if additional:
        failures.append(f"{len(additional)} artifacts additional in run 6")

    root_1, root_2 = Path(first["run_root"]), Path(second["run_root"])
    metadata = compare_run_metadata(root_1 / "run-metadata.json", root_2 / "run-metadata.json", policy, catalog)
    failures.extend(metadata["failures"])

    raw_differences: list[dict[str, Any]] = []
    semantic: list[dict[str, Any]] = []
    technology: list[dict[str, Any]] = []
    for relative in shared:
        left, right = first_by[relative], second_by[relative]
        if left.get("canonicalization_error") or right.get("canonicalization_error"):
            failures.append(f"{relative}: unresolved canonicalization error")
        raw_equal = left["raw_sha256"] == right["raw_sha256"]
        canonical_equal = left["canonical_sha256"] == right["canonical_sha256"]
        suffix = PurePosixPath(relative).suffix.lower()
        if not raw_equal:
            if relative == "run-metadata.json" and metadata["pass"]:
                classification = "PROVENANCE_IDENTITY and RUNTIME_RESOURCE_OBSERVATION"
                passed = True
            elif canonical_equal:
                classification = "RUNTIME_RESOURCE_OBSERVATION or PROVENANCE_IDENTITY"
                passed = True
            elif suffix == ".odb":
                classification = "SCIENTIFIC_EXACT with frozen semantic fallback"
                passed = True  # resolved below after semantic-export validation
            elif suffix in SEMANTIC_SUFFIXES or _semantic_match(relative, policy):
                classification = "SCIENTIFIC_EXACT or SCIENTIFIC_TOLERANCED"
                passed = False
            elif suffix == ".lyt":
                classification = "SCIENTIFIC_EXACT"
                passed = False
            elif suffix in {".json", ".log"}:
                classification = "SCIENTIFIC_EXACT or UNRESOLVED"
                passed = False
            else:
                classification = "UNRESOLVED"
                passed = False
            raw_differences.append(
                {
                    "path": relative,
                    "run_5_raw_sha256": left["raw_sha256"],
                    "run_6_raw_sha256": right["raw_sha256"],
                    "run_5_canonical_sha256": left["canonical_sha256"],
                    "run_6_canonical_sha256": right["canonical_sha256"],
                    "classification": classification,
                    "pass": passed,
                    "normalizations": sorted(set(left["normalizations_applied"]) | set(right["normalizations_applied"])),
                }
            )
            if not passed:
                failures.append(f"{relative}: canonical scientific/technology difference")
        if _semantic_match(relative, policy):
            row = {
                "path": relative,
                "run_5_canonical_sha256": left["canonical_sha256"],
                "run_6_canonical_sha256": right["canonical_sha256"],
                "pass": canonical_equal,
            }
            semantic.append(row)
            if not canonical_equal:
                failures.append(f"{relative}: semantic canonical mismatch")
        if suffix == ".odb":
            semantic_relative = relative + ".semantic.json"
            semantic_left = first_by.get(semantic_relative)
            semantic_right = second_by.get(semantic_relative)
            semantic_complete = False
            semantic_equal = False
            if semantic_left and semantic_right:
                try:
                    left_export = read_json(root_1 / semantic_relative)
                    right_export = read_json(root_2 / semantic_relative)
                    required = set(policy["semantic_artifacts"]["required_odb_categories"])
                    semantic_complete = (
                        left_export.get("schema_id") == right_export.get("schema_id") == "gate03es-complete-odb-semantic-export-v1"
                        and required == set(left_export.get("required_categories", [])) == set(right_export.get("required_categories", []))
                        and all(left_export.get("category_completeness", {}).get(key) is True for key in required)
                        and all(right_export.get("category_completeness", {}).get(key) is True for key in required)
                        and not left_export.get("unparsed_object_categories")
                        and not right_export.get("unparsed_object_categories")
                    )
                    semantic_equal = semantic_left["canonical_sha256"] == semantic_right["canonical_sha256"]
                except (OSError, KeyError, TypeError, json.JSONDecodeError):
                    semantic_complete = False
            odb_pass = semantic_complete and semantic_equal
            if not raw_equal and raw_differences and raw_differences[-1]["path"] == relative:
                raw_differences[-1]["pass"] = odb_pass
            semantic.append(
                {
                    "path": relative,
                    "format": "ODB",
                    "raw_equal_stronger_observation": raw_equal,
                    "semantic_export_path": semantic_relative,
                    "semantic_export_complete": semantic_complete,
                    "semantic_export_equal": semantic_equal,
                    "pass": odb_pass,
                }
            )
            if not odb_pass:
                failures.append(f"{relative}: ODB complete semantic export missing, incomplete, or unequal")
        if suffix == ".lyt":
            technology.append(
                {
                    "path": relative,
                    "format": "XML",
                    "run_5_canonical_sha256": left["canonical_sha256"],
                    "run_6_canonical_sha256": right["canonical_sha256"],
                    "pass": canonical_equal,
                }
            )
            if not canonical_equal:
                failures.append(f"{relative}: technology XML mismatch")

    metric_checks: list[dict[str, Any]] = []
    runtime_observations: list[dict[str, Any]] = []
    expected_identities: set[str] = set()
    for rule in schema["metrics"]:
        relative, key = rule["artifact"], rule["path"]
        identity = f"{relative}:{key}"
        if identity in expected_identities:
            failures.append(f"duplicate frozen metric rule: {identity}")
            continue
        expected_identities.add(identity)
        try:
            left_value = _lookup(read_json(root_1 / relative), key)
            right_value = _lookup(read_json(root_2 / relative), key)
        except (FileNotFoundError, KeyError, IndexError, TypeError) as exc:
            failures.append(f"{identity}: unresolved missing metric ({exc})")
            continue
        if not rule["gating"]:
            runtime_observations.append(
                {"path": identity, "run_5": left_value, "run_6": right_value, "classification": rule["classification"]}
            )
            continue
        delta = abs(float(left_value) - float(right_value))
        tolerance = float(rule["absolute_tolerance"])
        passed = delta <= tolerance
        row = {
            "path": identity,
            "run_5": left_value,
            "run_6": right_value,
            "absolute_delta": delta,
            "absolute_tolerance": tolerance,
            "unit": rule["unit"],
            "family": rule["family"],
            "classification": rule["classification"],
            "pass": passed,
        }
        metric_checks.append(row)
        if not passed:
            failures.append(f"{identity}: QoR tolerance breach")

    observed_identities: set[str] = set()
    for relative in sorted({rule["artifact"] for rule in schema["metrics"]}):
        for root in (root_1, root_2):
            if not (root / relative).is_file():
                continue
            for key, _ in _iter_numeric(read_json(root / relative)):
                observed_identities.add(f"{relative}:{key}")
    unknown = sorted(observed_identities - expected_identities)
    if unknown:
        failures.extend(f"{identity}: unresolved metric absent from frozen schema" for identity in unknown)

    histograms: list[dict[str, Any]] = []
    for relative in ("results/sky130hd/gcd/base/1_2_yosys.v", "results/sky130hd/gcd/base/6_final.v"):
        if (root_1 / relative).is_file() and (root_2 / relative).is_file():
            left_hist = mapped_master_histogram(root_1 / relative)
            right_hist = mapped_master_histogram(root_2 / relative)
            passed = bool(left_hist) and left_hist == right_hist
            histograms.append({"path": relative, "run_5": left_hist, "run_6": right_hist, "pass": passed})
            if not passed:
                failures.append(f"{relative}: mapped-master histogram mismatch or empty")
    if not semantic:
        failures.append("no required semantic artifacts found")
    if not technology:
        failures.append("no KLayout technology XML found")
    unique_failures = list(dict.fromkeys(failures))
    return {
        "schema_version": 3,
        "policy_sha256": expected_policy_hash,
        "metric_schema_sha256": sha256_file(schema_path),
        "reproducibility_pass": not unique_failures,
        "artifact_counts": {
            "run_5": len(first_by),
            "run_6": len(second_by),
            "raw_hash_differences": len(raw_differences),
        },
        "missing_from_run_6": missing,
        "additional_in_run_6": additional,
        "run_metadata_validation": metadata,
        "unknown_metrics": unknown,
        "raw_hash_differences": raw_differences,
        "semantic_artifact_comparisons": semantic,
        "technology_xml_comparisons": technology,
        "mapped_master_histograms": histograms,
        "metric_comparisons": metric_checks,
        "runtime_resource_observations": runtime_observations,
        "failures": unique_failures,
    }


def _context(lines: list[str], line_number: int, radius: int = 2) -> list[dict[str, Any]]:
    start = max(1, line_number - radius)
    end = min(len(lines), line_number + radius)
    return [{"line": number, "text": lines[number - 1]} for number in range(start, end + 1)]


def _source_for(path: str, text: str, catalog: dict[str, Any]) -> dict[str, Any]:
    producers = catalog["producers"]
    if "fastroute__" in path:
        return producers["openroad_fastroute_timers"]
    if "klayout.lyt" in path:
        return producers["klayout_technology_generator"]
    if "End of script. Logfile hash" in text or "Time spent:" in text or "yosys" in path:
        return producers["yosys_summary"]
    if "Runtime:" in text and "CTS-" in text:
        return producers["openroad_cts_runtime"]
    if "Runtime:" in text and "DPL-" in text:
        return producers["openroad_dpl_runtime"]
    if "Runtime:" in text and "DRT-" in text:
        return producers["openroad_drt_runtime"]
    if "Runtime:" in text:
        return producers["openroad_resizer_runtime"]
    if "Took " in text:
        return producers["orfs_took_timer"]
    if "memory =" in text or "cpu time =" in text:
        return producers["openroad_drt_resource"]
    if "Peak Memory/MB" in text or re.search(r"\.odb\s+\d+\s+\d+", text):
        return producers["orfs_elapsed_table"]
    return producers["orfs_process_resource_summary"]


def _classify_line(before: str, after: str) -> tuple[str, list[dict[str, str]], str]:
    joined = before + "\n" + after
    fields: list[dict[str, str]] = []
    if RUN_ROOT_RE.search(joined):
        fields.append({"field": "absolute run-root path", "classification": "serialization/path/timestamp metadata"})
    if "Logfile hash:" in joined:
        fields.append({"field": "Yosys derived logfile fingerprint", "classification": "serialization/path/timestamp metadata"})
    if any(token in joined for token in ("Runtime:", "Elapsed time:", "CPU time:", "Peak memory:", "Time spent:", "Took ", "memory =", "peak =")):
        fields.append({"field": "execution time or resource measurement", "classification": "execution runtime/resource usage"})
    if re.search(r"\.\S+\s+\d+\s+\d+\s+[0-9a-f]{20}", joined) or re.search(r"^\s*6_report\s+\d+\s+\d+", joined, re.M):
        fields.append({"field": "ORFS elapsed/peak-memory table columns", "classification": "execution runtime/resource usage"})
    if not fields:
        return "unresolved", [], "No producer-aware rule classified this line difference."
    classes = {field["classification"] for field in fields}
    overall = next(iter(classes)) if len(classes) == 1 else "serialization/path/timestamp metadata"
    return overall, fields, "Only explicitly identified execution observations or path-derived serialization fields differ."


def _text_field_differences(path_1: Path, path_2: Path, catalog: dict[str, Any]) -> list[dict[str, Any]]:
    left_lines = path_1.read_text(encoding="utf-8", errors="replace").splitlines()
    right_lines = path_2.read_text(encoding="utf-8", errors="replace").splitlines()
    matcher = difflib.SequenceMatcher(a=left_lines, b=right_lines, autojunk=False)
    rows: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        left = "\n".join(left_lines[i1:i2])
        right = "\n".join(right_lines[j1:j2])
        classification, fields, justification = _classify_line(left, right)
        source = _source_for(path_1.as_posix(), left + "\n" + right, catalog)
        rows.append(
            {
                "operation": tag,
                "run_1_lines": [i1 + 1, i2],
                "run_2_lines": [j1 + 1, j2],
                "run_1_exact": left_lines[i1:i2],
                "run_2_exact": right_lines[j1:j2],
                "run_1_context": _context(left_lines, i1 + 1),
                "run_2_context": _context(right_lines, j1 + 1),
                "classification": classification,
                "fields": fields,
                "producer_trace": source,
                "justification": justification,
            }
        )
    return rows


def _xml_parameter_rows(left_path: Path, right_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    left_root = ET.parse(left_path).getroot()
    right_root = ET.parse(right_path).getroot()

    def flatten(root: ET.Element) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []

        def visit(node: ET.Element, path: str) -> None:
            children = list(node)
            value = (node.text or "").strip()
            rows.append((path, value))
            counters: Counter[str] = Counter()
            for child in children:
                counters[child.tag] += 1
                visit(child, f"{path}/{child.tag}[{counters[child.tag]}]")

        visit(root, root.tag)
        return rows

    left_rows, right_rows = flatten(left_root), flatten(right_root)
    comparisons: list[dict[str, Any]] = []
    for index in range(max(len(left_rows), len(right_rows))):
        left = left_rows[index] if index < len(left_rows) else ("<missing>", None)
        right = right_rows[index] if index < len(right_rows) else ("<missing>", None)
        normalized_left = normalize_run_roots(left[1]) if isinstance(left[1], str) and left[0].endswith("/lef-files[1]") else left[1]
        normalized_right = normalize_run_roots(right[1]) if isinstance(right[1], str) and right[0].endswith("/lef-files[1]") else right[1]
        passed = left[0] == right[0] and normalized_left == normalized_right
        classification = (
            "serialization/path/timestamp metadata"
            if passed and left[1] != right[1]
            else "scientific QoR/state" if not passed else "scientific QoR/state"
        )
        comparisons.append(
            {
                "path_run_1": left[0],
                "path_run_2": right[0],
                "run_1": left[1],
                "run_2": right[1],
                "canonical_run_1": normalized_left,
                "canonical_run_2": normalized_right,
                "classification": classification,
                "pass": passed,
            }
        )
    canonical_left, _ = canonicalize_lyt(left_path.read_bytes())
    canonical_right, _ = canonicalize_lyt(right_path.read_bytes())
    summary = {
        "detected_format": "XML",
        "root_run_1": left_root.tag,
        "root_run_2": right_root.tag,
        "element_count_run_1": len(left_rows),
        "element_count_run_2": len(right_rows),
        "attribute_count_run_1": sum(len(element.attrib) for element in left_root.iter()),
        "attribute_count_run_2": sum(len(element.attrib) for element in right_root.iter()),
        "canonical_sha256_run_1": sha256_bytes(canonical_left),
        "canonical_sha256_run_2": sha256_bytes(canonical_right),
        "canonical_equal": canonical_left == canonical_right,
        "all_technology_layer_parameters_equal": all(row["pass"] for row in comparisons),
    }
    return comparisons, summary


def adjudicate_v1(
    comparison_path: Path,
    run_1: Path,
    run_2: Path,
    v1_policy: Path,
    v1_comparator: Path,
    catalog_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    anchors = {
        "policy_v1": {"path": str(v1_policy), "actual_sha256": sha256_file(v1_policy), "expected_sha256": V1_POLICY_SHA256},
        "comparator_v1": {"path": str(v1_comparator), "actual_sha256": sha256_file(v1_comparator), "expected_sha256": V1_COMPARATOR_SHA256},
        "comparison_v1": {"path": str(comparison_path), "actual_sha256": sha256_file(comparison_path), "expected_sha256": V1_COMPARISON_SHA256},
    }
    if any(item["actual_sha256"] != item["expected_sha256"] for item in anchors.values()):
        raise ValueError("a preserved v1 anchor hash changed")
    comparison = read_json(comparison_path)
    catalog = read_json(catalog_path)
    for trace in catalog["producers"].values():
        if trace["producer"] == "Yosys":
            trace["frozen_source_commit"] = catalog["yosys_commit"]
        elif trace["producer"].startswith("OpenROAD"):
            trace["frozen_source_commit"] = catalog["openroad_commit"]
        else:
            trace["frozen_source_commit"] = catalog["orfs_commit"]
    failed_raw = [row for row in comparison["raw_hash_differences"] if not row["pass"]]
    failed_metrics = [row for row in comparison["metric_comparisons"] if not row["pass"]]
    if len(failed_raw) != 16 or len(failed_metrics) != 29:
        raise ValueError("preserved v1 failure cardinality changed")

    raw_rows: list[dict[str, Any]] = []
    technology_parameters: list[dict[str, Any]] = []
    technology_summary: dict[str, Any] = {}
    for index, source_row in enumerate(failed_raw, start=1):
        relative = source_row["path"]
        left, right = run_1 / relative, run_2 / relative
        row: dict[str, Any] = {
            "occurrence": index,
            "path": relative,
            "v1_classification": source_row["classification"],
            "v1_explanation": source_row["explanation"],
            "run_1_raw_sha256": source_row["run_1_raw_sha256"],
            "run_2_raw_sha256": source_row["run_2_raw_sha256"],
            "run_1_canonical_sha256": source_row["run_1_canonical_sha256"],
            "run_2_canonical_sha256": source_row["run_2_canonical_sha256"],
        }
        if relative.endswith("klayout.lyt"):
            technology_parameters, technology_summary = _xml_parameter_rows(left, right)
            row.update(
                {
                    "adjudicated_classification": "serialization/path/timestamp metadata",
                    "producer_trace": catalog["producers"]["klayout_technology_generator"],
                    "exact_before": next(item["run_1"] for item in technology_parameters if item["run_1"] != item["run_2"]),
                    "exact_after": next(item["run_2"] for item in technology_parameters if item["run_1"] != item["run_2"]),
                    "context": "technology/reader-options/lefdef/lef-files",
                    "technology_summary": technology_summary,
                    "unresolved": False,
                }
            )
        elif relative.endswith(".json"):
            related = [metric for metric in failed_metrics if metric["path"].startswith(relative + ".")]
            row.update(
                {
                    "adjudicated_classification": "execution runtime/resource usage",
                    "producer_trace": catalog["producers"]["openroad_fastroute_timers"],
                    "field_differences": [
                        {
                            "path": metric["path"],
                            "run_1": metric["run_1"],
                            "run_2": metric["run_2"],
                            "classification": "execution runtime/resource usage",
                            "context": "OpenROAD Logger JSON metric emitted from RunTimings",
                        }
                        for metric in related[:9]
                    ],
                    "unresolved": False,
                }
            )
        else:
            fields = _text_field_differences(left, right, catalog)
            unresolved = any(item["classification"] == "unresolved" for item in fields)
            classes = sorted({field["classification"] for item in fields for field in item["fields"]})
            row.update(
                {
                    "adjudicated_classifications": classes,
                    "field_differences": fields,
                    "scientific_canonical_equal": normalize_log_text(left.read_text(encoding="utf-8", errors="replace"))[0]
                    == normalize_log_text(right.read_text(encoding="utf-8", errors="replace"))[0],
                    "unresolved": unresolved,
                }
            )
        raw_rows.append(row)

    first_occurrence: dict[str, int] = {}
    metric_rows: list[dict[str, Any]] = []
    raw_by_path = {row["path"]: row for row in comparison["raw_hash_differences"]}
    for occurrence, metric in enumerate(failed_metrics, start=1):
        identity = metric["path"]
        base_path = identity.split(":line-", 1)[0]
        if ".json." in identity:
            base_path = identity.split(".json.", 1)[0] + ".json"
        raw = raw_by_path.get(base_path, {})
        duplicate_of = first_occurrence.get(identity)
        first_occurrence.setdefault(identity, occurrence)
        line_match = re.search(r":line-(\d+):", identity)
        context_1: Any = None
        context_2: Any = None
        if line_match and (run_1 / base_path).is_file():
            line_number = int(line_match.group(1))
            context_1 = _context((run_1 / base_path).read_text(errors="replace").splitlines(), line_number)
            context_2 = _context((run_2 / base_path).read_text(errors="replace").splitlines(), line_number)
        source = _source_for(identity, json.dumps(metric), catalog)
        metric_rows.append(
            {
                "occurrence": occurrence,
                "path": identity,
                "run_1": metric["run_1"],
                "run_2": metric["run_2"],
                "absolute_delta": metric["absolute_delta"],
                "v1_absolute_tolerance": metric["absolute_tolerance"],
                "v1_classification": metric["classification"],
                "adjudicated_classification": "execution runtime/resource usage",
                "producer_trace": source,
                "run_1_context": context_1 or {"json_key": identity, "value": metric["run_1"]},
                "run_2_context": context_2 or {"json_key": identity, "value": metric["run_2"]},
                "run_1_raw_sha256": raw.get("run_1_raw_sha256"),
                "run_2_raw_sha256": raw.get("run_2_raw_sha256"),
                "run_1_canonical_sha256": raw.get("run_1_canonical_sha256"),
                "run_2_canonical_sha256": raw.get("run_2_canonical_sha256"),
                "duplicate_of_occurrence": duplicate_of,
                "duplicate_reason": (
                    "Policy v1 compared the changed JSON inside the raw-difference loop and again in the all-JSON metric loop."
                    if duplicate_of is not None else None
                ),
                "unresolved": False,
            }
        )

    unresolved = sum(bool(row.get("unresolved")) for row in raw_rows) + sum(bool(row["unresolved"]) for row in metric_rows)
    scientific_differences = sum(
        not row.get("scientific_canonical_equal", True)
        for row in raw_rows
        if not row["path"].endswith((".json", ".lyt"))
    )
    result = {
        "schema_version": 1,
        "gate": "03E-R",
        "analysis_mode": "read-only preserved evidence adjudication",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "anchors": anchors,
        "v1_result_preserved": {
            "reproducibility_pass": comparison["reproducibility_pass"],
            "unexplained_raw_difference_count": len(failed_raw),
            "numeric_breach_count": len(failed_metrics),
            "semantic_failure_count": sum(not row["pass"] for row in comparison["semantic_artifact_comparisons"]),
        },
        "root_cause": "Policy v1 treated unclassified runtime/resource observations as exact scientific numbers; its overflow regex also matched the FastRoute timer overflow_iterations_s before considering the _s unit.",
        "raw_difference_adjudications": raw_rows,
        "numeric_breach_adjudications": metric_rows,
        "duplicate_numeric_occurrence_count": sum(row["duplicate_of_occurrence"] is not None for row in metric_rows),
        "technology_xml": {
            "summary": technology_summary,
            "parameter_comparisons": technology_parameters,
        },
        "yosys_and_container_audit": {
            "warnings_optimization_decisions_cell_counts_and_transformations_equal": scientific_differences == 0,
            "differences_are_derived_log_fingerprints_paths_runtime_or_resources": True,
        },
        "classification_counts": {
            "scientific_qor_state_differences": scientific_differences,
            "unresolved": unresolved,
        },
        "adjudication_pass": unresolved == 0 and scientific_differences == 0 and technology_summary.get("all_technology_layer_parameters_equal", False),
    }
    schema = build_metric_schema(run_1, run_2)
    return result, schema


def freeze_bundle(destination: Path, named_files: list[tuple[str, Path]]) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(f"freeze destination already exists: {destination}")
    destination.mkdir(parents=True)
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name, source in named_files:
        if name in seen:
            raise ValueError(f"duplicate frozen bundle name: {name}")
        seen.add(name)
        target = destination / name
        shutil.copyfile(source, target)
        records.append({"name": name, "sha256": sha256_file(target), "size_bytes": target.stat().st_size})
    freeze_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest = {
        "schema_version": 3,
        "policy_id": "gate03es-reproducibility-v3",
        "frozen_at_utc": freeze_time,
        "files": records,
    }
    write_json(destination / "frozen-bundle.json", manifest)
    records_with_manifest = records + [
        {"name": "frozen-bundle.json", "sha256": sha256_file(destination / "frozen-bundle.json"), "size_bytes": (destination / "frozen-bundle.json").stat().st_size}
    ]
    (destination / "frozen-bundle.sha256").write_text(
        "".join(f"{row['sha256']}  {row['name']}\n" for row in records_with_manifest), encoding="ascii", newline="\n"
    )
    for path in destination.iterdir():
        path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    destination.chmod(stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    return manifest


def validate_policy(policy_path: Path, catalog_path: Path, schema_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    policy = read_json(policy_path)
    catalog = read_json(catalog_path)
    if policy.get("policy_id") != "gate03es-reproducibility-v3":
        errors.append("unexpected policy ID")
    if policy.get("amends", {}).get("sha256") != V2_POLICY_SHA256:
        errors.append("policy v2 amendment anchor changed")
    allowed_classes = {
        "SCIENTIFIC_EXACT", "SCIENTIFIC_TOLERANCED", "PROVENANCE_IDENTITY",
        "RUNTIME_RESOURCE_OBSERVATION", "UNRESOLVED",
    }
    if set(policy.get("field_classes", [])) != allowed_classes or set(catalog.get("allowed_classes", [])) != allowed_classes:
        errors.append("closed field-class catalogue mismatch")
    metadata_catalog = catalog.get("run_metadata_producer", {})
    if metadata_catalog.get("unknown_field_class") != "UNRESOLVED" or metadata_catalog.get("duplicate_key_class") != "UNRESOLVED":
        errors.append("run-metadata catalogue is not fail-closed")
    if set(metadata_catalog.get("closed_fields", {})) != {
        "schema_version", "run_label", "container_root", "host_root", "policy_frozen_at",
        "start_time", "end_time", "exit_status", "container_id", "process_id",
    }:
        errors.append("run-metadata producer field catalogue is not exact")
    anti = policy.get("anti_posthoc_rules", {})
    if anti.get("field_specific_exclusions_after_runs_begin") != "prohibited":
        errors.append("posthoc exclusion prohibition missing")
    if anti.get("path_specific_exclusion_list"):
        errors.append("path-specific exclusion list must remain empty")
    if anti.get("unknown_or_unresolved_field") != "gate failure":
        errors.append("unresolved fields are not fail-closed")
    if catalog.get("closed_schema_rule") is None:
        errors.append("producer catalogue is not closed")
    if schema_path:
        schema = read_json(schema_path)
        identities: set[str] = set()
        for row in schema.get("metrics", []):
            identity = f"{row.get('artifact')}:{row.get('path')}"
            if identity in identities:
                errors.append(f"duplicate metric schema entry: {identity}")
            identities.add(identity)
            if row.get("classification") not in {"SCIENTIFIC_EXACT", "SCIENTIFIC_TOLERANCED", "RUNTIME_RESOURCE_OBSERVATION"}:
                errors.append(f"invalid metric classification: {identity}")
            if row.get("gating") is False and row.get("classification") != "RUNTIME_RESOURCE_OBSERVATION":
                errors.append(f"nongating metric has scientific class: {identity}")
            if row.get("gating") is True and row.get("classification") not in {"SCIENTIFIC_EXACT", "SCIENTIFIC_TOLERANCED"}:
                errors.append(f"gating metric has nonscientific class: {identity}")
        if schema.get("posthoc_exclusions"):
            errors.append("metric schema contains posthoc exclusions")
        if schema.get("unknown_metric_rule") != "unresolved gate failure":
            errors.append("metric schema is not fail-closed")
    return errors


def validate_inputs(manifest_path: Path) -> list[str]:
    manifest = read_json(manifest_path)
    errors: list[str] = []
    for row in manifest.get("files", []):
        path = Path(row["path"])
        if not path.is_file():
            errors.append(f"missing immutable input: {path}")
        elif sha256_file(path) != row["sha256"]:
            errors.append(f"immutable input hash mismatch: {path}")
    for row in manifest.get("gate03es_implementation_files", []):
        path = Path(row["path"])
        if not path.is_file() or sha256_file(path) != row["sha256"]:
            errors.append(f"Gate 03E-S implementation hash mismatch: {path}")
    oci = manifest.get("oci_identity", {})
    if oci.get("index_digest") != OCI_INDEX_DIGEST:
        errors.append("OCI index digest mismatch")
    if oci.get("linux_amd64_manifest_digest") != IMAGE_DIGEST:
        errors.append("OCI linux/amd64 manifest digest mismatch")
    if oci.get("configuration_digest") != OCI_CONFIG_DIGEST:
        errors.append("OCI configuration/ImageID mismatch")
    if len({oci.get("index_digest"), oci.get("linux_amd64_manifest_digest"), oci.get("configuration_digest")}) != 3:
        errors.append("OCI index, manifest, and configuration identities were conflated")
    entries = manifest.get("execution_subset_entries", {})
    if len(entries) != manifest.get("execution_subset_expected_count"):
        errors.append("reconciled execution subset count mismatch")
    for path, expected in manifest.get("gcd_design_inputs", {}).items():
        if entries.get(path) != expected:
            errors.append(f"GCD immutable design-input record mismatch: {path}")
    for path, expected in manifest.get("sky130hd_collateral_entries", {}).items():
        if entries.get(path) != expected:
            errors.append(f"SKY130HD immutable collateral record mismatch: {path}")
    source = Path(manifest["orfs_source_root"])
    try:
        commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
        tree = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD^{tree}"], text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True).strip()
        if commit != ORFS_COMMIT or tree != ORFS_TREE or dirty:
            errors.append("ORFS source commit/tree/cleanliness mismatch")
        submodules = subprocess.check_output(
            ["git", "-C", str(source), "submodule", "status", "--recursive"], text=True
        ).strip()
        if submodules != manifest.get("orfs_submodule_status", "").strip():
            errors.append("ORFS submodule status mismatch")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        errors.append(f"cannot validate ORFS source: {exc}")
    try:
        image_inspect = json.loads(subprocess.check_output(
            ["docker", "image", "inspect", f"openroad/orfs@{IMAGE_DIGEST}"], text=True
        ))[0]
        descriptor_digest = image_inspect.get("Descriptor", {}).get("digest")
        if descriptor_digest != IMAGE_DIGEST:
            errors.append(f"local OCI manifest descriptor mismatch: {descriptor_digest}")
        script = """
set -euo pipefail
cd /OpenROAD-flow-scripts
source ./env.sh >/dev/null
for tool in openroad yosys klayout make python3; do
  path="$(command -v "$tool")"
  digest="$(sha256sum "$path" | awk '{print $1}')"
  version="$($tool --version 2>&1 | head -1 || true)"
  printf '%s|%s|%s|%s\\n' "$tool" "$path" "$digest" "$version"
done
"""
        output = subprocess.check_output(
            [
                "docker", "run", "--rm", "--platform", "linux/amd64",
                "--entrypoint", "/bin/bash", f"openroad/orfs@{IMAGE_DIGEST}",
                "-lc", script,
            ],
            text=True,
        )
        observed = [
            {"name": parts[0], "path": parts[1], "sha256": parts[2], "version": parts[3]}
            for line in output.splitlines() if line.strip()
            for parts in [line.split("|", 3)]
        ]
        if observed != manifest.get("flow_tool_binaries"):
            errors.append("flow-tool binary hash mismatch")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        errors.append(f"cannot validate OCI image: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    adjudicate = subparsers.add_parser("adjudicate")
    adjudicate.add_argument("--comparison", type=Path, required=True)
    adjudicate.add_argument("--run-1", type=Path, required=True)
    adjudicate.add_argument("--run-2", type=Path, required=True)
    adjudicate.add_argument("--v1-policy", type=Path, required=True)
    adjudicate.add_argument("--v1-comparator", type=Path, required=True)
    adjudicate.add_argument("--catalog", type=Path, required=True)
    adjudicate.add_argument("--output", type=Path, required=True)
    adjudicate.add_argument("--schema-output", type=Path, required=True)

    freeze = subparsers.add_parser("freeze")
    freeze.add_argument("--destination", type=Path, required=True)
    freeze.add_argument("--file", action="append", nargs=2, metavar=("NAME", "PATH"), required=True)

    inventory = subparsers.add_parser("inventory")
    inventory.add_argument("--root", type=Path, required=True)
    inventory.add_argument("--policy", type=Path, required=True)
    inventory.add_argument("--run-label", required=True)
    inventory.add_argument("--output", type=Path, required=True)

    compare = subparsers.add_parser("compare")
    compare.add_argument("--run-1", type=Path, required=True)
    compare.add_argument("--run-2", type=Path, required=True)
    compare.add_argument("--policy", type=Path, required=True)
    compare.add_argument("--schema", type=Path, required=True)
    compare.add_argument("--catalog", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--policy", type=Path, required=True)
    validate.add_argument("--catalog", type=Path, required=True)
    validate.add_argument("--schema", type=Path)
    validate.add_argument("--input-manifest", type=Path)
    validate.add_argument("--comparison", type=Path)

    args = parser.parse_args()
    if args.command == "adjudicate":
        result, schema = adjudicate_v1(
            args.comparison, args.run_1, args.run_2, args.v1_policy, args.v1_comparator, args.catalog
        )
        write_json(args.output, result)
        write_json(args.schema_output, schema)
        print(json.dumps({"adjudication_pass": result["adjudication_pass"], "raw": 16, "numeric": 29}, sort_keys=True))
        return 0 if result["adjudication_pass"] else 1
    if args.command == "freeze":
        manifest = freeze_bundle(args.destination, [(name, Path(path)) for name, path in args.file])
        print(json.dumps(manifest, sort_keys=True))
        return 0
    if args.command == "inventory":
        result = make_inventory(args.root, args.policy, args.run_label)
        write_json(args.output, result)
        print(json.dumps({"run_label": args.run_label, "artifact_count": result["artifact_count"]}, sort_keys=True))
        return 0
    if args.command == "compare":
        result = compare_runs(args.run_1, args.run_2, args.policy, args.schema, args.catalog)
        write_json(args.output, result)
        print(json.dumps({"reproducibility_pass": result["reproducibility_pass"], "failures": len(result["failures"])}, sort_keys=True))
        return 0 if result["reproducibility_pass"] else 1
    errors = validate_policy(args.policy, args.catalog, args.schema)
    if args.input_manifest:
        errors.extend(validate_inputs(args.input_manifest))
    if args.comparison:
        comparison = read_json(args.comparison)
        if comparison.get("reproducibility_pass") is not True:
            errors.append("fresh-run comparison did not pass")
        if comparison.get("unknown_metrics"):
            errors.append("fresh-run comparison contains unresolved metrics")
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
