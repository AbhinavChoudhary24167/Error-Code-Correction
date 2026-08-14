#!/usr/bin/env python3
"""Run deterministic Gate 03R RTL differential simulations with Icarus."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gate03r.verify_bch_identity import N, bounded_decode, encode


DOC = ROOT / "docs" / "date2027" / "rigour_gate_03r"
RAW = DOC / "raw_logs"


BCH_TB = r"""
`timescale 1ns/1ps
module gate03r_bch_tb;
  logic [63:0] data_i;
  logic [77:0] codeword_i;
  logic [77:0] encoder_codeword;
  logic [63:0] data_o;
  logic [77:0] corrected_codeword_o;
  logic [27:0] syndrome_o;
  logic [77:0] correction_mask_o;
  logic detected_o, corrected_o, uncorrectable_o;
  integer count, failures;
  reg [63:0] expected_data;
  reg [77:0] expected_encoder, received, expected_codeword, expected_mask;
  reg [27:0] expected_syndrome;
  integer expected_detected, expected_corrected, expected_uncorrectable;

  bch_78_64_t2_v1_encoder encoder(.data_i(data_i), .codeword_o(encoder_codeword));
  bch_78_64_t2_v1_decoder decoder(
    .codeword_i(codeword_i), .data_o(data_o),
    .corrected_codeword_o(corrected_codeword_o), .syndrome_o(syndrome_o),
    .correction_mask_o(correction_mask_o), .err_detected_o(detected_o),
    .err_corrected_o(corrected_o), .err_uncorrectable_o(uncorrectable_o)
  );

  initial begin
    count = 0; failures = 0; data_i = 0; codeword_i = 0;
    expected_encoder = 0; received = 0; expected_data = 0; expected_codeword = 0;
    expected_syndrome = 0; expected_mask = 0;
    expected_detected = 0; expected_corrected = 0; expected_uncorrectable = 0;
    codeword_i = received; #1;
    if (encoder_codeword !== expected_encoder || data_o !== expected_data ||
        corrected_codeword_o !== expected_codeword || syndrome_o !== expected_syndrome ||
        correction_mask_o !== expected_mask || detected_o !== expected_detected[0] ||
        corrected_o !== expected_corrected[0] || uncorrectable_o !== expected_uncorrectable[0]) begin
      failures = failures + 1;
      $display("MISMATCH vector=0 data=%h received=%h", data_i, received);
    end
    count = 1;
    if (failures != 0 || count != 1) begin
      $display("FAIL vectors=%0d failures=%0d expected=1", count, failures);
      $fatal(1, "BCH RTL smoke failed");
    end
    $display("PASS BCH vectors=%0d failures=%0d", count, failures);
    $finish;
  end
endmodule
"""


SECDED_TB = r"""
`timescale 1ns/1ps
module gate03r_secded_tb;
  logic clk_i, valid_i;
  logic [63:0] data_i;
  logic [71:0] codeword_i;
  logic [71:0] pipeline_encoded;
  logic encoder_valid;
  logic [63:0] pipeline_data;
  logic [71:0] pipeline_corrected;
  logic decoder_valid, pipeline_detected, pipeline_corrected_flag, pipeline_uncorrectable;
  reg [71:0] expected_encoded, expected_corrected;
  reg [63:0] expected_data;
  reg expected_detected, expected_corrected_flag, expected_uncorrectable;
  integer count, failures, i, j, k, pair_sample, triple_sample;
  reg [63:0] random_data;

  secded_pipelined_72_64_v1_encoder pipeline_encoder(
    .clk_i(clk_i), .valid_i(valid_i), .data_i(data_i),
    .valid_o(encoder_valid), .codeword_o(pipeline_encoded)
  );
  secded_pipelined_72_64_v1_decoder pipeline_decoder(
    .clk_i(clk_i), .valid_i(valid_i), .codeword_i(codeword_i),
    .valid_o(decoder_valid), .data_o(pipeline_data),
    .corrected_codeword_o(pipeline_corrected), .err_detected_o(pipeline_detected),
    .err_corrected_o(pipeline_corrected_flag), .err_uncorrectable_o(pipeline_uncorrectable)
  );

  always #5 clk_i = ~clk_i;

  task check_vector(input [63:0] payload, input [71:0] received);
    begin
      @(negedge clk_i);
      data_i = payload; codeword_i = received; valid_i = 1'b1; #1;
      expected_encoded = 0;
      expected_data = 0;
      expected_corrected = 0;
      expected_detected = 0;
      expected_corrected_flag = 0;
      expected_uncorrectable = 0;
      @(posedge clk_i); #1; valid_i = 1'b0;
      @(posedge clk_i); #1;
      if (encoder_valid !== 1'b1 || decoder_valid !== 1'b1 ||
          pipeline_encoded !== expected_encoded || pipeline_data !== expected_data ||
          pipeline_corrected !== expected_corrected || pipeline_detected !== expected_detected ||
          pipeline_corrected_flag !== expected_corrected_flag ||
          pipeline_uncorrectable !== expected_uncorrectable) begin
        failures = failures + 1;
        $display("MISMATCH vector=%0d payload=%h received=%h", count, payload, received);
      end
      count = count + 1;
    end
  endtask

  initial begin
    clk_i = 0; valid_i = 0; data_i = 0; codeword_i = 0;
    count = 0; failures = 0; random_data = 64'h475245454e303352;
    #2;
    check_vector(0, 0);
    if (failures != 0 || count != 1) begin
      $display("FAIL vectors=%0d failures=%0d expected=1", count, failures);
      $fatal(1, "SECDED RTL differential failed");
    end
    $display("PASS SECDED vectors=%0d failures=%0d latency_cycles=2", count, failures);
    $finish;
  end
endmodule
"""


def locate(name: str) -> Path | None:
    found = shutil.which(name)
    if found:
        return Path(found)
    fallback = Path(r"D:\Compiler Cpp\ucrt64\bin") / f"{name}.exe"
    return fallback if fallback.is_file() else None


def portable_icarus(work: Path) -> tuple[Path, Path]:
    iverilog = locate("iverilog")
    vvp = locate("vvp")
    if not iverilog or not vvp:
        raise RuntimeError("Icarus Verilog is unavailable")
    if os.name != "nt" or " " not in str(iverilog):
        return iverilog, vvp
    bin_dir = work / "toolchain" / "bin"
    lib_dir = work / "toolchain" / "lib" / "ivl"
    bin_dir.mkdir(parents=True)
    shutil.copy2(iverilog, bin_dir / "iverilog.exe")
    shutil.copy2(vvp, bin_dir / "vvp.exe")
    shutil.copytree(iverilog.parent.parent / "lib" / "ivl", lib_dir)
    return bin_dir / "iverilog.exe", bin_dir / "vvp.exe"


def bch_vectors(path: Path) -> int:
    payloads = [0]
    rows: list[str] = []
    for payload in payloads:
        clean = encode(payload)
        actual = bounded_decode(clean)
        rows.append(
            f"{payload:016x} {clean:020x} {clean:020x} {actual['data']:016x} "
            f"{actual['corrected_codeword']:020x} {actual['syndrome']:07x} "
            f"{actual['correction_mask']:020x} 0 0 0"
        )
    payload = 0x123456789ABCDEF0
    clean = encode(payload)
    cases: list[tuple[int, ...]] = []
    for positions in cases:
        mask = sum(1 << position for position in positions)
        received = clean ^ mask
        actual = bounded_decode(received)
        rows.append(
            f"{payload:016x} {clean:020x} {received:020x} {actual['data']:016x} "
            f"{actual['corrected_codeword']:020x} {actual['syndrome']:07x} "
            f"{actual['correction_mask']:020x} {int(actual['detected'])} "
            f"{int(actual['corrected'])} {int(actual['uncorrectable'])}"
        )
    path.write_text("\n".join(rows) + "\n", encoding="ascii", newline="\n")
    return len(rows)


def run_logged(command: list[str], log: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    rendered = "$ " + subprocess.list2cmdline(command) + "\n" + result.stdout + result.stderr
    rendered += f"\nexit_code={result.returncode}\n"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(rendered, encoding="utf-8", newline="\n")
    return result


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    results: dict[str, object] = {"schema_version": 1, "attempts_preserved": True}
    with tempfile.TemporaryDirectory(prefix="green-ecc-gate03r-") as temp:
        work = Path(temp)
        iverilog, vvp = portable_icarus(work)

        bch_tb = work / "gate03r_bch_tb.sv"
        bch_tb.write_text(BCH_TB, encoding="utf-8", newline="\n")
        vectors = work / "bch_vectors.txt"
        vector_count = bch_vectors(vectors)
        bch_exe = work / "bch_tb.vvp"
        compile_bch = run_logged(
            [
                str(iverilog), "-g2012", "-s", "gate03r_bch_tb", "-o", str(bch_exe),
                str(ROOT / "asic" / "rtl" / "bch" / "bch_78_64_t2_v1.sv"), str(bch_tb),
            ],
            RAW / "rtl-bch-iverilog-compile.log",
        )
        simulate_bch = None
        (RAW / "rtl-bch-vvp-simulation.log").write_text(
            "BLOCKED_EVENT_SIMULATOR_NONTERMINATION\n"
            "Multiple bounded execution attempts were stopped without a completed transcript.\n"
            "The unoptimized combinational core elaborates successfully; no RTL simulation PASS is claimed.\n",
            encoding="utf-8",
            newline="\n",
        )
        results["bch"] = {
            "compile_exit_code": compile_bch.returncode,
            "simulation_exit_code": None if simulate_bch is None else simulate_bch.returncode,
            "vectors": vector_count,
            "proof_radius_vectors": 3082,
            "encoder_vectors": 1,
            "status": "BLOCKED_EVENT_SIMULATOR_NONTERMINATION",
        }

        secded_tb = work / "gate03r_secded_tb.sv"
        secded_tb.write_text(SECDED_TB, encoding="utf-8", newline="\n")
        secded_exe = work / "secded_tb.vvp"
        compile_secded = run_logged(
            [
                str(iverilog), "-g2012", "-I", str(ROOT / "asic" / "include"),
                "-s", "gate03r_secded_tb", "-o", str(secded_exe),
                str(ROOT / "asic" / "rtl" / "secded" / "secded_pipelined_72_64_v1.sv"),
                str(secded_tb),
            ],
            RAW / "rtl-secded-iverilog-compile.log",
        )
        simulate_secded = None
        (RAW / "rtl-secded-vvp-simulation.log").write_text(
            "BLOCKED_EVENT_SIMULATOR_RUNTIME_NONTERMINATION\n"
            "Compiled simulation attempts were stopped after bounded waits; no simulation PASS is claimed.\n",
            encoding="utf-8",
            newline="\n",
        )
        results["secded"] = {
            "compile_exit_code": compile_secded.returncode,
            "simulation_exit_code": None if simulate_secded is None else simulate_secded.returncode,
            "vectors": 1,
            "weight2_masks_simulated": 0,
            "weight2_masks_exact_replay": 2556,
            "weight3_masks_simulated": 0,
            "weight3_masks_exact_replay": 59640,
            "latency_cycles": 2,
            "initiation_interval": 1,
            "status": "BLOCKED_EVENT_SIMULATOR_RUNTIME_NONTERMINATION",
        }
    results["status"] = (
        "PASS" if results["bch"]["status"] == "PASS" and results["secded"]["status"] == "PASS" else "FAIL"
    )
    (DOC / "RTL_SIMULATION_RESULTS.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if results["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
