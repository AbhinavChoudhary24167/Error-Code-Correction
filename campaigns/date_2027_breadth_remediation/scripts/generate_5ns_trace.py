#!/usr/bin/env python3
"""Generate the predeclared 5 ns conventional-SECDED no-error input trace."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path


MASK64 = (1 << 64) - 1
OPERATIONS = 100000
PAYLOAD_SEED = 104375203646206
FAULT_SEED = 7085774586302733229
PERIOD_NS = 5.0


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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite trace: {args.out}")
    args.out.parent.mkdir(parents=True, exist_ok=True)

    raw_hash = hashlib.sha256()
    raw_bytes = 0
    binary = gzip.GzipFile(filename=str(args.out), mode="wb", compresslevel=9, mtime=0)
    text = io.TextIOWrapper(binary, encoding="ascii", newline="\n", write_through=True)

    def write(value: str) -> None:
        nonlocal raw_bytes
        encoded = value.encode("ascii")
        raw_hash.update(encoded)
        raw_bytes += len(encoded)
        text.write(value)

    half_ps = 2500
    write(
        "$date\n  FROZEN_DATE2027_BREADTH_TRACE\n$end\n"
        "$version\n  breadth generate_5ns_trace.py\n$end\n"
        "$timescale 1ps $end\n$scope module gate04_trace_top $end\n"
        "$var wire 1 ! clk_i $end\n$var wire 1 \" rst_ni $end\n"
        "$var wire 64 # enc_data_i [63:0] $end\n"
        "$var wire 72 $ dec_codeword_i [71:0] $end\n"
        "$var wire 1 % valid_i $end\n$upscope $end\n$enddefinitions $end\n"
        f"#0\n0!\n0\"\nb{'0' * 64} #\nb{'0' * 72} $\n0%\n"
    )
    time_ps = 0
    for _ in range(6):
        time_ps += half_ps
        write(f"#{time_ps}\n1!\n")
        time_ps += half_ps
        write(f"#{time_ps}\n0!\n")

    payload_state = PAYLOAD_SEED & MASK64
    for _ in range(OPERATIONS):
        payload_state, payload = splitmix64(payload_state)
        received = secded_encode(payload)
        write(f"#{time_ps}\n1\"\n1%\nb{payload:064b} #\nb{received:072b} $\n")
        time_ps += half_ps
        write(f"#{time_ps}\n1!\n")
        time_ps += half_ps
        write(f"#{time_ps}\n0!\n")
    write(f"#{time_ps}\n0%\nb{'0' * 64} #\nb{'0' * 72} $\n")
    for _ in range(4):
        time_ps += half_ps
        write(f"#{time_ps}\n1!\n")
        time_ps += half_ps
        write(f"#{time_ps}\n0!\n")
    text.close()

    payload = {
        "family": "conventional_secded",
        "codeword_width_bits": 72,
        "clock_period_ns": PERIOD_NS,
        "trace_class": "no_error",
        "useful_operations": OPERATIONS,
        "total_time_ps": time_ps,
        "payload_seed": PAYLOAD_SEED,
        "fault_schedule_seed": FAULT_SEED,
        "file": args.out.name,
        "compressed_bytes": args.out.stat().st_size,
        "compressed_sha256": file_sha256(args.out),
        "uncompressed_bytes": raw_bytes,
        "uncompressed_sha256": raw_hash.hexdigest(),
        "generator_sha256": file_sha256(Path(__file__)),
        "methodology_relation": "same Gate-04 primary-input sequence and reset/flush policy, with only the predeclared period changed to 5 ns"
    }
    args.record.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
