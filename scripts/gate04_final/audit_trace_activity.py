#!/usr/bin/env python3
"""Count value-change and bit-toggle activity in the frozen Gate 04 VCDs."""

from __future__ import annotations

import argparse
import gzip
import json
import re
from pathlib import Path


VAR_RE = re.compile(r"^\$var\s+\S+\s+(\d+)\s+(\S+)\s+(.+?)\s+\$end$")


def count_trace(path: Path) -> dict[str, object]:
    variables: dict[str, dict[str, object]] = {}
    previous: dict[str, str] = {}
    in_definitions = True

    with gzip.open(path, "rt", encoding="ascii", newline="") as stream:
        for raw_line in stream:
            line = raw_line.strip()
            if not line:
                continue
            if in_definitions:
                match = VAR_RE.match(line)
                if match:
                    width, identifier, reference = match.groups()
                    variables[identifier] = {
                        "name": reference,
                        "width_bits": int(width),
                        "value_change_events": 0,
                        "bit_transitions": 0,
                    }
                elif line == "$enddefinitions $end":
                    in_definitions = False
                continue
            if line[0] in "01xXzZ":
                value, identifier = line[0].lower(), line[1:]
            elif line[0] in "bB":
                pieces = line[1:].split(maxsplit=1)
                if len(pieces) != 2:
                    continue
                value, identifier = pieces[0].lower(), pieces[1]
            else:
                continue
            if identifier not in variables:
                continue
            width = int(variables[identifier]["width_bits"])
            value = value.zfill(width)
            old = previous.get(identifier)
            if old is not None and old != value:
                variables[identifier]["value_change_events"] = (
                    int(variables[identifier]["value_change_events"]) + 1
                )
                variables[identifier]["bit_transitions"] = (
                    int(variables[identifier]["bit_transitions"])
                    + sum(left != right for left, right in zip(old, value))
                )
            previous[identifier] = value

    ordered = sorted(variables.values(), key=lambda item: str(item["name"]))
    return {
        "signals": ordered,
        "total_value_change_events": sum(int(item["value_change_events"]) for item in ordered),
        "total_bit_transitions": sum(int(item["bit_transitions"]) for item in ordered),
        "non_clock_value_change_events": sum(
            int(item["value_change_events"]) for item in ordered if item["name"] != "clk_i"
        ),
        "non_clock_bit_transitions": sum(
            int(item["bit_transitions"]) for item in ordered if item["name"] != "clk_i"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest_path = args.trace_root / "TRACE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = []
    for record in manifest["traces"]:
        path = args.trace_root / record["file"]
        counts = count_trace(path)
        rows.append(
            {
                "family": record["family"],
                "trace_class": record["trace_class"],
                "file": record["file"],
                "compressed_sha256": record["compressed_sha256"],
                **counts,
            }
        )
    payload = {
        "schema_version": 1,
        "method": "direct read-only VCD value-change count; vector bit transitions are Hamming distances between successive values",
        "initial_assignments_counted_as_transitions": False,
        "rows": rows,
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
