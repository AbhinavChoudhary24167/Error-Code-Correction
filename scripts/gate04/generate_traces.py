#!/usr/bin/env python3
"""Generate deterministic, result-blind Gate 04 primary-input VCD traces."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path


MASK64 = (1 << 64) - 1
ROOT = Path(__file__).resolve().parents[2]


def splitmix64(value: int) -> tuple[int, int]:
    state = (value + 0x9E3779B97F4A7C15) & MASK64
    z = state
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
    return state, (z ^ (z >> 31)) & MASK64


def secded_encode(data: int) -> int:
    positional = 0
    data_index = 0
    for position in range(1, 72):
        if position & (position - 1):
            positional |= ((data >> data_index) & 1) << (position - 1)
            data_index += 1
    for parity_index in range(7):
        parity = 0
        for position in range(1, 72):
            if position & (1 << parity_index):
                parity ^= (positional >> (position - 1)) & 1
        positional |= parity << ((1 << parity_index) - 1)
    return positional | ((positional.bit_count() & 1) << 71)


def bch_encode(data: int) -> int:
    polynomial = 0b101010001111101
    work = data << 14
    for dividend_index in range(77, 13, -1):
        if (work >> dividend_index) & 1:
            work ^= polynomial << (dividend_index - 14)
    return ((work & ((1 << 14) - 1)) << 64) | data


def hsiao_rows() -> list[int]:
    payload = json.loads((ROOT / "docs/date2027/rigour_gate_02/CANONICAL_CODE_SPECS.json").read_text(encoding="utf-8"))
    spec = next(item for item in payload["specifications"] if item["code_id"] == "hsiao-secded-72-64-v1")
    rows: list[int] = []
    for row in spec["G"]:
        rows.append(sum(int(bit) << index for index, bit in enumerate(row)))
    if len(rows) != 64 or any(row.bit_length() > 72 for row in rows):
        raise ValueError("invalid frozen Hsiao G matrix")
    return rows


def linear_encode(data: int, rows: list[int]) -> int:
    result = 0
    for index, row in enumerate(rows):
        if (data >> index) & 1:
            result ^= row
    return result


class VcdWriter:
    def __init__(self, path: Path, width: int):
        self.path = path
        self.width = width
        self.raw_hash = hashlib.sha256()
        self.raw_bytes = 0
        self._binary = gzip.GzipFile(filename=str(path), mode="wb", compresslevel=9, mtime=0)
        self._text = io.TextIOWrapper(self._binary, encoding="ascii", newline="\n", write_through=True)

    def write(self, text: str) -> None:
        data = text.encode("ascii")
        self.raw_hash.update(data)
        self.raw_bytes += len(data)
        self._text.write(text)

    def close(self) -> None:
        self._text.close()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def emit_trace(
    path: Path,
    *,
    family: str,
    width: int,
    period_ns: float,
    trace_class: str,
    operations: int,
    payload_seed: int,
    fault_seed: int,
    hsiao: list[int],
) -> dict[str, object]:
    encode = {
        "conventional_secded": secded_encode,
        "hsiao": lambda data: linear_encode(data, hsiao),
        "bch78": bch_encode,
    }[family]
    half_ps = int(round(period_ns * 1000 / 2))
    if half_ps * 2 != int(round(period_ns * 1000)):
        raise ValueError("period must map to an even number of picoseconds")

    writer = VcdWriter(path, width)
    writer.write(
        "$date\n  FROZEN_DETERMINISTIC_GATE04_TRACE\n$end\n"
        "$version\n  GREEN-ECC Gate 04 generate_traces.py\n$end\n"
        "$timescale 1ps $end\n$scope module gate04_trace_top $end\n"
        "$var wire 1 ! clk_i $end\n$var wire 1 \" rst_ni $end\n"
        "$var wire 64 # enc_data_i [63:0] $end\n"
        f"$var wire {width} $ dec_codeword_i [{width - 1}:0] $end\n"
        "$var wire 1 % valid_i $end\n$upscope $end\n$enddefinitions $end\n"
        f"#0\n0!\n0\"\nb{'0' * 64} #\nb{'0' * width} $\n0%\n"
    )
    time_ps = 0
    # Six frozen reset clocks flush every internal valid pipeline.
    for _ in range(6):
        time_ps += half_ps
        writer.write(f"#{time_ps}\n1!\n")
        time_ps += half_ps
        writer.write(f"#{time_ps}\n0!\n")

    payload_state = payload_seed & MASK64
    fault_state = fault_seed & MASK64
    for _ in range(operations):
        payload_state, payload = splitmix64(payload_state)
        clean = encode(payload)
        fault_state, q1 = splitmix64(fault_state)
        fault_state, q2 = splitmix64(fault_state)
        first = (q1 * width) >> 64
        second = (q2 * width) >> 64
        while second == first:
            second = (second + 1) % width
        if trace_class == "no_error":
            received = clean
        elif trace_class == "single_error":
            received = clean ^ (1 << first)
        elif trace_class == "double_error":
            received = clean ^ (1 << first) ^ (1 << second)
        else:
            raise ValueError(trace_class)
        writer.write(
            f"#{time_ps}\n1\"\n1%\nb{payload:064b} #\nb{received:0{width}b} $\n"
        )
        time_ps += half_ps
        writer.write(f"#{time_ps}\n1!\n")
        time_ps += half_ps
        writer.write(f"#{time_ps}\n0!\n")

    writer.write(f"#{time_ps}\n0%\nb{'0' * 64} #\nb{'0' * width} $\n")
    for _ in range(4):
        time_ps += half_ps
        writer.write(f"#{time_ps}\n1!\n")
        time_ps += half_ps
        writer.write(f"#{time_ps}\n0!\n")
    raw_sha = writer.raw_hash.hexdigest()
    raw_bytes = writer.raw_bytes
    writer.close()
    return {
        "family": family,
        "codeword_width_bits": width,
        "clock_period_ns": period_ns,
        "trace_class": trace_class,
        "useful_operations": operations,
        "total_time_ps": time_ps,
        "payload_seed": payload_seed,
        "fault_schedule_seed": fault_seed,
        "position_mapping": "floor(q*N/2^64); second coordinate cyclically advanced only on equality",
        "file": path.name,
        "compressed_bytes": path.stat().st_size,
        "compressed_sha256": file_sha256(path),
        "uncompressed_bytes": raw_bytes,
        "uncompressed_sha256": raw_sha,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=ROOT / "scripts/gate04/contract_v1.json")
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=False)
    activity = contract["activity"]
    rows: list[dict[str, object]] = []
    hsiao = hsiao_rows()
    for family, width in (("conventional_secded", 72), ("hsiao", 72), ("bch78", 78)):
        for period in contract["physical_experiment"]["clock_periods_ns"]:
            for trace_class in activity["trace_classes"]:
                name = f"{family}-{int(period)}ns-{trace_class}.vcd.gz"
                rows.append(
                    emit_trace(
                        args.out / name,
                        family=family,
                        width=width,
                        period_ns=float(period),
                        trace_class=trace_class,
                        operations=int(activity["payload_operations_per_trace"]),
                        payload_seed=int(activity["payload_seed"]),
                        fault_seed=int(activity["fault_schedule_seed"]),
                        hsiao=hsiao,
                    )
                )
    manifest = {
        "schema_version": 1,
        "generator_sha256": file_sha256(Path(__file__)),
        "traces": rows,
    }
    (args.out / "TRACE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"GATE04_TRACES_GENERATED count={len(rows)} operations_each={activity['payload_operations_per_trace']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
