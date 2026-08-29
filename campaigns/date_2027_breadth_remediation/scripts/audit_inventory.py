#!/usr/bin/env python3
"""Create or verify the immutable Revision-2 breadth-campaign baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


EXTERNAL_ROOT = "/var/lib/green-ecc-date2027-revision2"
LOCAL_SCOPES = (
    "docs/date2027/revision2",
    "scripts/revision2",
    "paper/date2027_revision2",
)
PROTECTED_SOURCES = (
    "asic/rtl/bch/bch_78_64_t2_v1.sv",
    "asic/rtl/secded/secded_pipelined_72_64_v1.sv",
    "scripts/gate03r/rtl/secded_characterization_tops.sv",
    "scripts/gate04/rtl/gate04_boundaries.sv",
    "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv",
    "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv",
    "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_decoder.sv",
    "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v2_algorithmic_decoder.sv",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_root() -> Path:
    return Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True, encoding="utf-8"
        ).strip()
    )


def local_inventory(repo: Path) -> dict[str, str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z", "--", *LOCAL_SCOPES],
        cwd=repo,
        stdout=subprocess.PIPE,
        check=True,
    )
    paths = {
        item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item
    }
    paths.update(PROTECTED_SOURCES)
    records: dict[str, str] = {}
    for relative in sorted(paths):
        path = repo / relative
        if not path.is_file():
            raise SystemExit(f"missing protected repository file: {relative}")
        records[f"repository/{relative}"] = sha256(path)
    return records


def external_inventory() -> dict[str, str]:
    script = (
        "set -eu; "
        f"test -d {EXTERNAL_ROOT}; "
        f"find {EXTERNAL_ROOT} -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum"
    )
    completed = subprocess.run(
        ["wsl", "-d", "Ubuntu-24.04", "--", "sh", "-lc", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(f"external inventory failed: {completed.stderr.strip()}")
    records: dict[str, str] = {}
    prefix = f"{EXTERNAL_ROOT}/"
    for line in completed.stdout.splitlines():
        expected, absolute = line.split(maxsplit=1)
        absolute = absolute.lstrip("* ")
        if not absolute.startswith(prefix):
            raise SystemExit(f"unexpected external inventory path: {absolute}")
        records[f"external-rev2/{absolute.removeprefix(prefix)}"] = expected
    return records


def current_inventory(repo: Path) -> dict[str, str]:
    records = local_inventory(repo)
    overlap = set(records).intersection(external_inventory())
    if overlap:
        raise SystemExit(f"inventory key collision: {sorted(overlap)[:3]}")
    records.update(external_inventory())
    return records


def load_manifest(path: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        expected, key = line.split(maxsplit=1)
        key = key.strip()
        if key in records:
            raise SystemExit(f"duplicate key on line {line_number}: {key}")
        records[key] = expected
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", type=Path)
    group.add_argument("--verify", type=Path)
    parser.add_argument("--result-json", type=Path)
    args = parser.parse_args()

    repo = repository_root()
    local = local_inventory(repo)
    external = external_inventory()
    current = local | external
    result: dict[str, object] = {
        "algorithm": "sha256-raw-bytes",
        "baseline_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True, encoding="utf-8"
        ).strip(),
        "repository_file_count": len(local),
        "external_revision2_file_count": len(external),
        "total_file_count": len(current),
    }

    if args.write is not None:
        output = args.write if args.write.is_absolute() else repo / args.write
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "".join(f"{current[key]}  {key}\n" for key in sorted(current)),
            encoding="utf-8",
            newline="\n",
        )
        result.update({"status": "BASELINE_WRITTEN", "manifest": str(output)})
    else:
        manifest = args.verify if args.verify.is_absolute() else repo / args.verify
        expected = load_manifest(manifest)
        missing = sorted(set(expected) - set(current))
        added = sorted(set(current) - set(expected))
        changed = sorted(key for key in set(expected) & set(current) if expected[key] != current[key])
        status = "PASS" if not (missing or added or changed) else "FAIL"
        result.update(
            {
                "status": status,
                "manifest": str(manifest),
                "missing": missing,
                "added": added,
                "changed": changed,
            }
        )

    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(encoded, end="")
    if args.result_json is not None:
        output = args.result_json if args.result_json.is_absolute() else repo / args.result_json
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8", newline="\n")
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
