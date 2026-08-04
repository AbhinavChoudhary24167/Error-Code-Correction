#!/usr/bin/env python3
"""Audit every unique generated parity-check matrix retained in reports/."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codeforge.equivalence import classify_code


def walk(value: Any, source: str, found: dict[str, dict[str, Any]]) -> None:
    if isinstance(value, dict):
        if all(key in value for key in ("H", "G", "k", "r", "n", "decoder")):
            digest = hashlib.sha256(json.dumps(value["H"], separators=(",", ":")).encode()).hexdigest()
            record = found.setdefault(digest, {"code": value, "sources": []})
            if source not in record["sources"]:
                record["sources"].append(source)
        for child in value.values():
            walk(child, source, found)
    elif isinstance(value, list):
        for child in value:
            walk(child, source, found)


def main() -> None:
    found: dict[str, dict[str, Any]] = {}
    for path in sorted((ROOT / "reports").rglob("*.json")):
        try:
            walk(json.loads(path.read_text(encoding="utf-8")), path.relative_to(ROOT).as_posix(), found)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    references = {}
    for path in sorted((ROOT / "reports").rglob("odd_column_secded_code.json")):
        code = json.loads(path.read_text(encoding="utf-8"))
        references[(int(code["k"]), int(code["r"]))] = code
    audits = []
    for digest, record in sorted(found.items(), key=lambda item: (int(item[1]["code"]["n"]), item[0])):
        code = record["code"]
        dims = (int(code["k"]), int(code["r"]))
        reference = references.get(dims)
        geometry = {"rows": 2, "columns": 4} if int(code["n"]) == 8 else {"rows": 8, "columns": 9} if int(code["n"]) == 72 else None
        audit = classify_code(code, reference_code=reference, geometry=geometry)
        audit["matrix_sha256"] = digest
        audit["source_files"] = sorted(record["sources"])
        audits.append(audit)
    output = ROOT / "reports" / "safeforge_study" / "all_code_equivalence_audits.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "unique_matrix_count": len(audits),
                "audit_scope": "all recursively discoverable H/G/code objects in tracked reports JSON",
                "audits": audits,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"unique_matrix_count": len(audits), "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
