"""Shared-graph SystemVerilog emitters for generated portfolios."""

from __future__ import annotations

import math
import re
from typing import Any, Mapping, Sequence


def _identifier(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"ecc_{cleaned}"
    return cleaned.lower()


def _token_expression(token: int, input_width: int, input_name: str) -> str:
    return f"{input_name}[{token}]" if token < input_width else f"z_{token}"


def _graph_wires(graph: Mapping[str, Any], input_name: str) -> tuple[str, list[str]]:
    input_width = int(graph["input_width"])
    declarations = [f"  logic z_{int(node['node_id'])};" for node in graph["nodes"]]
    assignments = [
        "  assign z_{node} = {left} ^ {right};".format(
            node=int(node["node_id"]),
            left=_token_expression(int(node["left"]), input_width, input_name),
            right=_token_expression(int(node["right"]), input_width, input_name),
        )
        for node in graph["nodes"]
    ]
    return "\n".join(declarations + assignments), [str(item) for item in declarations]


def _output_expression(record: Mapping[str, Any], input_width: int, input_name: str) -> str:
    tokens = [int(token) for token in record["tokens"]]
    if not tokens:
        return "1'b0"
    return " ^ ".join(_token_expression(token, input_width, input_name) for token in tokens)


def render_shared_portfolio_rtl(portfolio: Mapping[str, Any]) -> dict[str, str]:
    portfolio_id = _identifier(str(portfolio["portfolio_id"]))
    codes = list(portfolio["modes"])
    k, r, n = int(portfolio["k"]), int(portfolio["r"]), int(portfolio["n"])
    mode_width = max(1, math.ceil(math.log2(len(codes))))
    graph = portfolio["shared_graph"]

    encoder_graph = graph["encoder"]
    encoder_wires, _ = _graph_wires(encoder_graph, "data")
    encoder_cases: list[str] = []
    for mode_index, code in enumerate(codes):
        lines = []
        for parity in range(r):
            label = f"{code['code_id']}:parity:{parity}"
            expression = _output_expression(encoder_graph["outputs"][label], k, "data")
            lines.append(f"        parity[{parity}] = {expression};")
        encoder_cases.append(
            f"      {mode_width}'d{mode_index}: begin\n" + "\n".join(lines) + "\n      end"
        )
    encoder = f'''// Generated from the certified shared XOR graph; structural only.
module {portfolio_id}_encoder(
  input  logic [{mode_width - 1}:0] mode,
  input  logic [{k - 1}:0] data,
  output logic [{n - 1}:0] codeword
);
  logic [{r - 1}:0] parity;
{encoder_wires}
  always_comb begin
    parity = '0;
    unique case (mode)
{chr(10).join(encoder_cases)}
      default: begin end
    endcase
  end
  assign codeword[{k - 1}:0] = data;
  assign codeword[{n - 1}:{k}] = parity;
endmodule
'''

    syndrome_graph = graph["syndrome"]
    syndrome_wires, _ = _graph_wires(syndrome_graph, "word")
    syndrome_cases: list[str] = []
    for mode_index, code in enumerate(codes):
        lines = []
        for row in range(r):
            label = f"{code['code_id']}:syndrome:{row}"
            expression = _output_expression(syndrome_graph["outputs"][label], n, "word")
            lines.append(f"        syndrome[{row}] = {expression};")
        syndrome_cases.append(
            f"      {mode_width}'d{mode_index}: begin\n" + "\n".join(lines) + "\n      end"
        )
    syndrome = f'''// Generated from the certified shared XOR graph; structural only.
module {portfolio_id}_syndrome(
  input  logic [{mode_width - 1}:0] mode,
  input  logic [{n - 1}:0] word,
  output logic [{r - 1}:0] syndrome
);
{syndrome_wires}
  always_comb begin
    syndrome = '0;
    unique case (mode)
{chr(10).join(syndrome_cases)}
      default: begin end
    endcase
  end
endmodule
'''

    decoder_cases: list[str] = []
    for mode_index, code in enumerate(codes):
        for entry in code["decoder"]["correction_entries"]:
            mask = sum(1 << int(position) for position in entry["positions"])
            decoder_cases.append(
                f"      {{{mode_width}'d{mode_index}, {r}'b{entry['syndrome']}}}: begin "
                f"correction_known = 1'b1; correction_mask = {n}'b{mask:0{n}b}; end"
            )
    decoder = f'''// Generated configurable correction table; configuration integrity is external.
module {portfolio_id}_decoder(
  input  logic [{mode_width - 1}:0] mode,
  input  logic [{n - 1}:0] word,
  output logic [{k - 1}:0] data_out,
  output logic correction_applied,
  output logic detected_uncorrectable
);
  logic [{r - 1}:0] syndrome;
  logic [{n - 1}:0] correction_mask;
  logic [{n - 1}:0] corrected_word;
  logic correction_known;
  {portfolio_id}_syndrome u_syndrome(.mode(mode), .word(word), .syndrome(syndrome));
  always_comb begin
    correction_known = 1'b0;
    correction_mask = '0;
    unique case ({{mode, syndrome}})
{chr(10).join(decoder_cases)}
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
        f"{portfolio_id}_encoder.sv": encoder,
        f"{portfolio_id}_syndrome.sv": syndrome,
        f"{portfolio_id}_decoder.sv": decoder,
    }


def render_portfolio_testbench(portfolio: Mapping[str, Any]) -> tuple[str, str]:
    portfolio_id = _identifier(str(portfolio["portfolio_id"]))
    codes = list(portfolio["modes"])
    assignments = list(portfolio["assignments"].items())
    k, n = int(portfolio["k"]), int(portfolio["n"])
    mode_width = max(1, math.ceil(math.log2(len(codes))))
    checks: list[str] = []
    for mode_index, (regime_id, _) in enumerate(assignments):
        report = portfolio["certificates"][regime_id]
        checks.append(f"    mode = {mode_width}'d{mode_index};")
        for pattern in report["per_pattern"]:
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
                    f"    received = codeword ^ {n}'b{mask:0{n}b}; #1;",
                    f"    if ({condition}) $fatal(1, \"mode {mode_index} pattern {pattern['pattern_id']} failed\");",
                ]
            )
    tb = f'''`timescale 1ns/1ps
module tb_{portfolio_id};
  logic [{mode_width - 1}:0] mode;
  logic [{k - 1}:0] data;
  logic [{n - 1}:0] codeword, received;
  logic [{k - 1}:0] data_out;
  logic correction_applied, detected_uncorrectable;
  {portfolio_id}_encoder u_encoder(.mode(mode), .data(data), .codeword(codeword));
  {portfolio_id}_decoder u_decoder(
    .mode(mode), .word(received), .data_out(data_out),
    .correction_applied(correction_applied),
    .detected_uncorrectable(detected_uncorrectable)
  );
  initial begin
    data = '0; #1;
{chr(10).join(checks)}
    data = '1; #1;
{chr(10).join(checks)}
    $display("PASS tb_{portfolio_id}");
    $finish;
  end
endmodule
'''
    return f"tb_{portfolio_id}.sv", tb
