from __future__ import annotations

"""Metadata helpers for factual plot provenance."""

from datetime import datetime, timezone
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping


def git_hash() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_metadata(path: Path, metadata: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(metadata), indent=2, sort_keys=True), encoding="utf-8")


__all__ = ["git_hash", "utc_timestamp", "write_metadata"]
