"""Narrow additive-path compatibility for historical gate validators.

This adapter does not authorize changes inside any historical evidence tree.
It only recognizes separately named, explicitly registered additive gate paths;
byte identity of historical trees is enforced by Gate 03E-S manifests.
"""

from __future__ import annotations

from pathlib import PurePosixPath


REGISTERED_ADDITIVE_PREFIXES = (
    "docs/date2027/rigour_gate_03er/",
    "scripts/gate03er/",
    "tests/python/test_gate03er_reproducibility.py",
    "docs/date2027/rigour_gate_03es/",
    "scripts/gate03es/",
    "tests/python/test_gate03es_",
    "docs/date2027/rigour_gate_03f/",
    "scripts/gate03f/",
    "tests/python/test_gate03f_",
    "docs/date2027/rigour_gate_04/",
    "scripts/gate04/",
    "docs/date2027/rigour_gate_04_final/",
    "scripts/gate04_final/",
    "tests/python/test_gate04_",
    "docs/date2027/rigour_gate_05/",
    "scripts/gate05/",
    "tests/python/test_gate05_",
    "docs/date2027/rigour_gate_06/",
    "scripts/gate06/",
    "tests/python/test_gate06_",
    "docs/date2027/rigour_gate_07/",
    "scripts/gate07/",
    "tests/python/test_gate07_",
    # Closed DATE manuscript and the separately named prospective Revision-2
    # campaign.  These paths are additive; no historical evidence prefix below
    # is broadened or made writable by this compatibility registry.
    "DATE2027_FINAL_AUDIT.md",
    "DATE2027_MANUSCRIPT_FREEZE.json",
    "DATE2027_REVIEWER_SIMULATION.md",
    "GATE08_RELATED_WORK_AUDIT.md",
    "output/pdf/date2027_submission.pdf",
    "paper/date2027/",
    "docs/date2027/revision2/",
    "paper/date2027_revision2/",
    "scripts/revision2/",
    "tests/python/test_revision2_",
    "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v2_algorithmic_decoder.sv",
    # Render-only manuscript QA output; never authoritative evidence.
    "tmp/pdfs/",
)

HISTORICAL_EVIDENCE_PREFIXES = (
    "docs/date2027/rigour_gate_01/",
    "docs/date2027/rigour_gate_02/",
    "docs/date2027/rigour_gate_03/",
    "docs/date2027/rigour_gate_03r/",
    "docs/date2027/rigour_gate_03e/",
)


def normalized_repo_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("/") or ".." in PurePosixPath(normalized).parts:
        return ""
    return normalized


def is_registered_additive_path(path: str) -> bool:
    normalized = normalized_repo_path(path)
    return bool(normalized) and normalized.startswith(REGISTERED_ADDITIVE_PREFIXES)


def is_scope_path_allowed(path: str, historical_validator_allowlist: tuple[str, ...]) -> bool:
    normalized = normalized_repo_path(path)
    return bool(normalized) and (
        normalized.startswith(historical_validator_allowlist)
        or is_registered_additive_path(normalized)
    )
