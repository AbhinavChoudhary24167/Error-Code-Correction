"""Reference-model and synthesizable RTL emitters for certified codes."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from .gf2 import matrix_columns_as_ints


def _identifier(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"ecc_{cleaned}"
    return cleaned.lower()


def _decoder_pairs(code: Mapping[str, Any]) -> list[tuple[int, int]]:
    n = int(code["n"])
    pairs: list[tuple[int, int]] = []
    for entry in code["decoder"]["correction_entries"]:
        syndrome_value = int(entry["syndrome"], 2)
        mask = sum(1 << int(position) for position in entry["positions"])
        if mask >= (1 << n):
            raise ValueError("decoder mask exceeds code width")
        pairs.append((syndrome_value, mask))
    return sorted(pairs)


def render_python_reference(code: Mapping[str, Any]) -> str:
    columns = matrix_columns_as_ints(code["H"])
    pairs = _decoder_pairs(code)
    return f'''#!/usr/bin/env python3
"""Generated bit-exact reference for {code["code_id"]}."""
from __future__ import annotations
import argparse

K = {int(code["k"])}
R = {int(code["r"])}
N = {int(code["n"])}
H_COLUMNS = {columns!r}
G = {code["G"]!r}
DECODER = {dict(pairs)!r}

def syndrome(word: int) -> int:
    value = 0
    for position, column in enumerate(H_COLUMNS):
        if (word >> position) & 1:
            value ^= column
    return value

def encode(data: int) -> int:
    if data < 0 or data >= (1 << K):
        raise ValueError("data does not fit")
    out = 0
    for bit in range(N):
        value = 0
        for source in range(K):
            value ^= ((data >> source) & 1) & G[source][bit]
        out |= value << bit
    return out

def decode(received: int, original_data: int | None = None) -> dict:
    syn = syndrome(received)
    if syn == 0:
        decoded = received & ((1 << K) - 1)
        outcome = "correct" if original_data is None or decoded == original_data else "silent_corruption"
        return {{"outcome": outcome, "syndrome": syn, "decoded_data": decoded, "correction_mask": 0}}
    if syn not in DECODER:
        return {{"outcome": "detected_uncorrectable", "syndrome": syn, "decoded_data": None, "correction_mask": 0}}
    mask = DECODER[syn]
    corrected = received ^ mask
    if syndrome(corrected) != 0:
        return {{"outcome": "decoder_failure", "syndrome": syn, "decoded_data": None, "correction_mask": mask}}
    decoded = corrected & ((1 << K) - 1)
    outcome = "corrected" if original_data is None or decoded == original_data else "silent_corruption"
    return {{"outcome": outcome, "syndrome": syn, "decoded_data": decoded, "correction_mask": mask}}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=lambda value: int(value, 0))
    parser.add_argument("error_mask", type=lambda value: int(value, 0))
    args = parser.parse_args()
    codeword = encode(args.data)
    result = decode(codeword ^ args.error_mask, args.data)
    print(f"{{codeword}} {{codeword ^ args.error_mask}} {{result['syndrome']}} {{result['outcome']}} {{result['decoded_data'] if result['decoded_data'] is not None else -1}}")

if __name__ == "__main__":
    main()
'''


def render_cpp_reference(code: Mapping[str, Any]) -> str:
    columns = matrix_columns_as_ints(code["H"])
    pairs = _decoder_pairs(code)
    g_rows = [sum(int(bit) << index for index, bit in enumerate(row)) for row in code["G"]]
    decoder_cases = "\n".join(
        f"        case {syndrome_value}ULL: mask = {mask}ULL; known = true; break;"
        for syndrome_value, mask in pairs
    )
    return f'''// Generated bit-exact reference for {code["code_id"]}.
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>

static constexpr unsigned K = {int(code["k"])};
static constexpr unsigned R = {int(code["r"])};
static constexpr unsigned N = {int(code["n"])};
static constexpr std::uint64_t H_COLUMNS[N] = {{{", ".join(str(value) + "ULL" for value in columns)}}};
static constexpr std::uint64_t G_ROWS[K] = {{{", ".join(str(value) + "ULL" for value in g_rows)}}};

std::uint64_t syndrome(std::uint64_t word) {{
    std::uint64_t value = 0;
    for (unsigned position = 0; position < N; ++position) if ((word >> position) & 1ULL) value ^= H_COLUMNS[position];
    return value;
}}

std::uint64_t encode(std::uint64_t data) {{
    std::uint64_t out = 0;
    for (unsigned source = 0; source < K; ++source) if ((data >> source) & 1ULL) out ^= G_ROWS[source];
    return out;
}}

int main(int argc, char** argv) {{
    if (argc != 3) return 2;
    const std::uint64_t data = std::stoull(argv[1], nullptr, 0);
    const std::uint64_t error = std::stoull(argv[2], nullptr, 0);
    const std::uint64_t codeword = encode(data);
    const std::uint64_t received = codeword ^ error;
    const std::uint64_t syn = syndrome(received);
    std::uint64_t mask = 0;
    bool known = false;
    switch (syn) {{
{decoder_cases}
        default: break;
    }}
    std::string outcome;
    long long decoded = -1;
    if (syn == 0) {{
        decoded = static_cast<long long>(received & ((1ULL << K) - 1ULL));
        outcome = decoded == static_cast<long long>(data) ? "correct" : "silent_corruption";
    }} else if (!known) {{
        outcome = "detected_uncorrectable";
    }} else {{
        const std::uint64_t corrected = received ^ mask;
        if (syndrome(corrected) != 0) outcome = "decoder_failure";
        else {{
            decoded = static_cast<long long>(corrected & ((1ULL << K) - 1ULL));
            outcome = decoded == static_cast<long long>(data) ? "corrected" : "silent_corruption";
        }}
    }}
    std::cout << codeword << ' ' << received << ' ' << syn << ' ' << outcome << ' ' << decoded << '\\n';
    return 0;
}}
'''


def render_systemverilog(code: Mapping[str, Any]) -> dict[str, str]:
    code_id = _identifier(str(code["code_id"]))
    k, r, n = int(code["k"]), int(code["r"]), int(code["n"])
    h = code["H"]
    g = code["G"]
    encoder_lines = [f"  assign codeword[{index}] = data[{index}];" for index in range(k)]
    for parity in range(r):
        sources = [f"data[{data}]" for data in range(k) if int(g[data][k + parity])]
        expression = " ^ ".join(sources) if sources else "1'b0"
        encoder_lines.append(f"  assign codeword[{k + parity}] = {expression};")
    encoder = f'''// Generated structural encoder; no technology-specific PPA claim.
module {code_id}_encoder(
  input  logic [{k - 1}:0] data,
  output logic [{n - 1}:0] codeword
);
{chr(10).join(encoder_lines)}
endmodule
'''
    syndrome_lines: list[str] = []
    for row in range(r):
        sources = [f"word[{position}]" for position in range(n) if int(h[row][position])]
        expression = " ^ ".join(sources) if sources else "1'b0"
        syndrome_lines.append(f"  assign syndrome[{row}] = {expression};")
    syndrome_module = f'''// Generated syndrome network; no technology-specific PPA claim.
module {code_id}_syndrome(
  input  logic [{n - 1}:0] word,
  output logic [{r - 1}:0] syndrome
);
{chr(10).join(syndrome_lines)}
endmodule
'''
    case_lines = []
    for syndrome_value, mask in _decoder_pairs(code):
        case_lines.append(
            f"      {r}'b{syndrome_value:0{r}b}: begin correction_known = 1'b1; correction_mask = {n}'b{mask:0{n}b}; end"
        )
    decoder = f'''// Generated hard-decision syndrome decoder.
module {code_id}_decoder(
  input  logic [{n - 1}:0] word,
  output logic [{k - 1}:0] data_out,
  output logic correction_applied,
  output logic detected_uncorrectable
);
  logic [{r - 1}:0] syndrome;
  logic [{n - 1}:0] correction_mask;
  logic [{n - 1}:0] corrected_word;
  logic correction_known;
  {code_id}_syndrome u_syndrome(.word(word), .syndrome(syndrome));
  always_comb begin
    correction_known = 1'b0;
    correction_mask = '0;
    unique case (syndrome)
{chr(10).join(case_lines)}
      default: begin end
    endcase
  end
  assign correction_applied = (syndrome != '0) && correction_known;
  assign detected_uncorrectable = (syndrome != '0) && !correction_known;
  assign corrected_word = word ^ correction_mask;
  assign data_out = corrected_word[{k - 1}:0];
endmodule
'''
    return {
        f"{code_id}_encoder.sv": encoder,
        f"{code_id}_syndrome.sv": syndrome_module,
        f"{code_id}_decoder.sv": decoder,
    }


def render_testbench(code: Mapping[str, Any], per_pattern: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    code_id = _identifier(str(code["code_id"]))
    k, n = int(code["k"]), int(code["n"])
    checks: list[str] = []
    for pattern in per_pattern:
        mask = sum(1 << int(position) for position in pattern["positions"])
        outcome = str(pattern["outcome"])
        if outcome in {"correct", "corrected"}:
            condition = "data_out !== data"
        elif outcome == "detected_uncorrectable":
            condition = "!detected_uncorrectable"
        elif outcome == "silent_corruption":
            condition = "detected_uncorrectable || data_out === data"
        else:
            condition = "1'b1"
        checks.extend(
            [
                f"      received = codeword ^ {n}'b{mask:0{n}b}; #1;",
                f"      if ({condition}) $fatal(1, \"pattern {pattern['pattern_id']} failed for data=%0d\", d);",
            ]
        )
    tb = f'''`timescale 1ns/1ps
module tb_{code_id};
  logic [{k - 1}:0] data;
  logic [{n - 1}:0] codeword, received;
  logic [{k - 1}:0] data_out;
  logic correction_applied, detected_uncorrectable;
  integer d;
  {code_id}_encoder u_encoder(.data(data), .codeword(codeword));
  {code_id}_decoder u_decoder(
    .word(received), .data_out(data_out),
    .correction_applied(correction_applied),
    .detected_uncorrectable(detected_uncorrectable)
  );
  initial begin
    for (d = 0; d < {1 << k}; d = d + 1) begin
      data = d[{k - 1}:0]; #1;
{chr(10).join(checks)}
    end
    $display("PASS tb_{code_id}");
    $finish;
  end
endmodule
'''
    return f"tb_{code_id}.sv", tb
