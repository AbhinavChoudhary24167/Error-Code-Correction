"""Synthesizable SafeForge policy RTL and bit-exact regression testbenches."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from .artifacts import render_systemverilog
from .gf2 import matrix_columns_as_ints


def _identifier(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]", "_", value).lower()
    return value if value and not value[0].isdigit() else "ecc_" + value


def render_safe_rtl(policy: Mapping[str, Any]) -> dict[str, str]:
    code = policy["compiled_code"]
    code_id = _identifier(str(code["code_id"]))
    k, r, n = int(code["k"]), int(code["r"]), int(code["n"])
    envelope_hex = str(policy["policy_sha256"])[:32]
    base = render_systemverilog(code)
    base = {name: content for name, content in base.items() if not name.endswith("_decoder.sv")}
    cases = []
    for entry in code["decoder"]["correction_entries"]:
        mask = sum(1 << int(position) for position in entry["positions"])
        cases.append(
            f"      {r}'b{entry['syndrome']}: begin action_correct = 1'b1; correction_mask = {n}'b{mask:0{n}b}; end"
        )
    decoder = f'''// SafeForge certified abstaining syndrome policy.
module {code_id}_safe_decoder(
  input  logic [{n - 1}:0] word,
  input  logic envelope_valid,
  input  logic fallback_select,
  output logic [{k - 1}:0] data_out,
  output logic correction_applied,
  output logic abstain,
  output logic detected_uncorrectable,
  output logic fallback_selected,
  output logic no_certified_mode,
  output logic [127:0] safety_envelope_id
);
  logic [{r - 1}:0] syndrome;
  logic [{n - 1}:0] correction_mask;
  logic [{n - 1}:0] corrected_word;
  logic action_correct;
  {code_id}_syndrome u_syndrome(.word(word), .syndrome(syndrome));
  always_comb begin
    action_correct = 1'b0;
    correction_mask = '0;
    unique case (syndrome)
{chr(10).join(cases)}
      default: begin end
    endcase
  end
  assign safety_envelope_id = 128'h{envelope_hex};
  assign fallback_selected = !envelope_valid && fallback_select;
  assign no_certified_mode = !envelope_valid && !fallback_select;
  assign correction_applied = envelope_valid && (syndrome != '0) && action_correct;
  assign abstain = (syndrome != '0) && (!envelope_valid || !action_correct);
  assign detected_uncorrectable = abstain;
  assign corrected_word = word ^ ({{{n}{{correction_applied}}}} & correction_mask);
  assign data_out = corrected_word[{k - 1}:0];
endmodule
'''
    base[f"{code_id}_safe_decoder.sv"] = decoder
    return base


def render_safe_testbench(
    policy: Mapping[str, Any], outcomes: Sequence[Mapping[str, Any]]
) -> tuple[str, str]:
    code = policy["compiled_code"]
    code_id = _identifier(str(code["code_id"]))
    k, n = int(code["k"]), int(code["n"])
    checks = []
    for outcome in outcomes:
        mask = sum(1 << int(position) for position in outcome["positions"])
        expected = str(outcome["outcome"])
        if expected in {"correct", "corrected"}:
            condition = "due || data_out !== data"
        elif expected == "detected_uncorrectable":
            condition = "!due"
        elif expected == "silent_corruption":
            condition = "due || data_out === data"
        else:
            condition = "1'b1"
        checks.extend(
            [
                f"      received = codeword ^ {n}'b{mask:0{n}b}; #1;",
                f"      if ({condition}) $fatal(1, \"policy mismatch for {outcome['pattern_id']} data=%0d\", d);",
            ]
        )
    rendered_checks = chr(10).join(checks)
    if k <= 12:
        campaign = f'''    for (d = 0; d < {1 << k}; d = d + 1) begin
      data = d[{k - 1}:0]; #1;
{rendered_checks}
    end'''
        campaign_kind = "all data words crossed with every modeled error"
    else:
        alternating_a = int("10" * (k // 2) + ("1" if k % 2 else ""), 2)
        alternating_5 = ((1 << k) - 1) ^ alternating_a
        assignments = [0, (1 << k) - 1, alternating_a, alternating_5]
        blocks = []
        for index, value in enumerate(assignments):
            blocks.append(
                f"    d = {index}; data = {k}'h{value:0{(k + 3) // 4}x}; #1;\n{rendered_checks}"
            )
        campaign = "\n".join(blocks)
        campaign_kind = "four linearity representatives crossed with every modeled error"
    tb = f'''`timescale 1ns/1ps
module tb_{code_id}_safe;
  // Campaign: {campaign_kind}.
  logic [{k - 1}:0] data;
  logic [{n - 1}:0] codeword, received;
  logic [{k - 1}:0] data_out;
  logic correction_applied, abstain, due, fallback_selected, no_certified_mode, envelope_valid;
  logic [127:0] safety_envelope_id;
  integer d;
  {code_id}_encoder u_encoder(.data(data), .codeword(codeword));
  {code_id}_safe_decoder u_decoder(
    .word(received), .envelope_valid(envelope_valid), .fallback_select(1'b1),
    .data_out(data_out), .correction_applied(correction_applied), .abstain(abstain),
    .detected_uncorrectable(due), .fallback_selected(fallback_selected),
    .no_certified_mode(no_certified_mode), .safety_envelope_id(safety_envelope_id)
  );
  initial begin
    envelope_valid = 1'b1;
{campaign}
    received = codeword ^ 1; #1;
    envelope_valid = 1'b0; #1;
    if (!due || !fallback_selected || correction_applied) $fatal(1, "out-of-envelope fallback failed");
    $display("PASS tb_{code_id}_safe");
    $finish;
  end
endmodule
'''
    return f"tb_{code_id}_safe.sv", tb


def policy_hardware_comparison(
    nominal_code: Mapping[str, Any], safe_policy: Mapping[str, Any]
) -> dict[str, Any]:
    nominal_entries = list(nominal_code["decoder"]["correction_entries"])
    safe_entries = list(safe_policy["compiled_code"]["decoder"]["correction_entries"])
    return {
        "cost_model": "technology-independent syndrome-table structural counts",
        "physical_ppa": None,
        "nominal_entries": len(nominal_entries),
        "safe_correction_entries": len(safe_entries),
        "safe_abstain_entries": int(safe_policy["abstention_count"]),
        "added_control_bits": 3,
        "added_metadata_bits": 128,
        "correction_entries_removed": len(nominal_entries) - len(safe_entries),
        "interpretation": (
            "Abstention changes table contents and adds control/metadata; this is not a cell-area, "
            "timing, power, or physical-PPA result."
        ),
    }
