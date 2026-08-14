from __future__ import annotations

import json
import struct
from pathlib import Path

from scripts.gate03e.reproducibility import (
    canonicalize_gds,
    compare_json_metrics,
    normalize_text,
    read_policy,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = read_policy(ROOT / "scripts/gate03e/reproducibility_policy_v1.json")


def _record(record_type: int, data_type: int = 0, payload: bytes = b"") -> bytes:
    if len(payload) % 2:
        payload += b"\0"
    return struct.pack(">HBB", len(payload) + 4, record_type, data_type) + payload


def _element(layer: int, coordinate: int) -> bytes:
    return b"".join(
        [
            _record(0x08),
            _record(0x0D, 2, struct.pack(">h", layer)),
            _record(0x0E, 2, struct.pack(">h", 0)),
            _record(0x10, 3, struct.pack(">10i", *([coordinate] * 10))),
            _record(0x11),
        ]
    )


def _structure(name: str, date_byte: int, elements: list[bytes]) -> bytes:
    return b"".join(
        [
            _record(0x05, 2, bytes([date_byte]) * 24),
            _record(0x06, 6, name.encode("ascii")),
            *elements,
            _record(0x07),
        ]
    )


def _gds(date_byte: int, structures: list[bytes]) -> bytes:
    return b"".join(
        [
            _record(0x00, 2, struct.pack(">h", 600)),
            _record(0x01, 2, bytes([date_byte]) * 24),
            _record(0x02, 6, b"gate03e"),
            *structures,
            _record(0x04),
        ]
    )


def test_gds_dates_structure_order_and_element_order_are_predeclared() -> None:
    alpha_a = _structure("alpha", 1, [_element(2, 20), _element(1, 10)])
    beta_a = _structure("beta", 1, [_element(3, 30)])
    alpha_b = _structure("alpha", 9, [_element(1, 10), _element(2, 20)])
    beta_b = _structure("beta", 9, [_element(3, 30)])
    first = _gds(1, [beta_a, alpha_a])
    second = _gds(9, [alpha_b, beta_b])
    assert first != second
    assert canonicalize_gds(first) == canonicalize_gds(second)


def test_only_predeclared_text_metadata_is_normalized() -> None:
    first = (
        "run_id=/gate03e-run-01\r\n"
        "Elapsed time: 0:00.31[h:]min:sec CPU time: user 0.2 Peak memory: 12KB  \r\n"
        "WARNING design area is 12.5\r\n"
    )
    second = (
        "run_id=/gate03e-run-02\n"
        "Elapsed time: 0:00.99[h:]min:sec CPU time: user 0.9 Peak memory: 99KB\n"
        "WARNING design area is 12.5\n"
    )
    normalized_first, actions = normalize_text(first, POLICY)
    normalized_second, _ = normalize_text(second, POLICY)
    assert normalized_first == normalized_second
    assert "WARNING design area is 12.5" in normalized_first
    assert "absolute_run_root" in actions


def test_area_is_an_exact_invariant() -> None:
    checks: list[dict[str, object]] = []
    issues = compare_json_metrics(
        {"design__instance__area": 10.0},
        {"design__instance__area": 10.0000001},
        "metrics.json",
        POLICY,
        checks,
    )
    assert issues
    assert checks[0]["classification"] == "exact_invariant"
    assert checks[0]["absolute_tolerance"] == 0.0


def test_timing_tolerance_is_frozen_at_one_microsecond_in_ns() -> None:
    checks: list[dict[str, object]] = []
    issues = compare_json_metrics(
        {"timing__setup__ws": -0.1},
        {"timing__setup__ws": -0.1000005},
        "metrics.json",
        POLICY,
        checks,
    )
    assert not issues
    assert checks[0]["absolute_tolerance"] == 1e-6
    assert checks[0]["pass"] is True


def test_unclassified_numeric_metric_requires_exact_equality() -> None:
    checks: list[dict[str, object]] = []
    issues = compare_json_metrics(
        {"novel_metric": 1.0},
        {"novel_metric": 1.0000000001},
        "metrics.json",
        POLICY,
        checks,
    )
    assert issues
    assert checks[0]["classification"] == "unclassified_numeric_exact"
    assert checks[0]["absolute_tolerance"] == 0.0


def test_policy_is_stable_json() -> None:
    value = json.loads((ROOT / "scripts/gate03e/reproducibility_policy_v1.json").read_text())
    assert value["policy_id"] == "gate03e-reproducibility-v1"
    assert value["canonicalization"]["unordered_row_sets"] == []
