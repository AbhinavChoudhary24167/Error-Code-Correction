#!/usr/bin/env python3
"""Execute one fresh matched physical/activity/power job under the v3.3 deadline.

This script is intentionally campaign-specific.  It reuses the frozen v3.2
ORFS configuration without modifying it, preserves every attempt, produces
post-route gate-level VCD activity, and performs parasitic-aware OpenROAD power
analysis.  The SRAM behavioral models expose interface behaviour for GLS, but
their Liberty views do not establish complete macro-internal energy; emitted
E5 records are therefore limited to the non-macro logic boundary.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from typing import Any, Iterable, Mapping, Sequence


IMAGE = "openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
CAMPAIGN_REL = Path("campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5")
PARENT_REL = Path("campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation")
MACRO_REL = Path(
    "campaigns/iscas_sustainability_extension/memory_compiler/"
    "gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"
)
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
STDCELL_LIBERTY = "/OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
OPERATIONS = (
    "IDLE",
    "WRITE_CLEAN",
    "READ_CLEAN",
    "READ_SINGLE_BIT_ERROR_CORRECT",
    "READ_DOUBLE_BIT_ERROR_DETECT",
)
ARCHITECTURES: dict[str, dict[str, Any]] = {
    "SECDED": {
        "top": "secded_matched_sram_top",
        "config": "secded.mk",
        "encoder_module": "gate03r_secded_baseline_encoder",
        "encoder_port": ".data_i(data), .codeword_o(codeword)",
        "encoder_sources": ["scripts/gate03r/rtl/secded_characterization_tops.sv"],
        "rtl_sources": ["scripts/gate03r/rtl/secded_characterization_tops.sv"],
    },
    "HSIAO_SECDED": {
        "top": "hsiao_matched_sram_top",
        "config": "hsiao.mk",
        "encoder_module": "hsiao_secded_72_64_v1_encoder",
        "encoder_port": ".data(data), .codeword(codeword)",
        "encoder_sources": [
            "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv"
        ],
        "rtl_sources": [
            "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv",
            "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv",
            "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_decoder.sv",
        ],
    },
}


class CampaignCutoff(RuntimeError):
    """The one persisted campaign deadline was reached."""


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def copy_preserved(source: Path, destination: Path) -> None:
    """Copy once or verify an existing immutable copy; never overwrite evidence."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        if sha256(source) != sha256(destination):
            raise RuntimeError(f"refusing to overwrite differing preserved evidence: {destination}")
        return
    shutil.copy2(source, destination)


def gzip_preserved(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return
    with source.open("rb") as incoming, destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as outgoing:
            shutil.copyfileobj(incoming, outgoing)


def load_deadline(runtime_state: Path) -> tuple[dict[str, Any], float]:
    state = json.loads(runtime_state.read_text(encoding="utf-8"))
    if state.get("budget_scope") != "ENTIRE_CAMPAIGN" or state.get("campaign_budget_seconds") != 54000:
        raise RuntimeError("runtime state is not the authoritative 54,000-second ENTIRE_CAMPAIGN budget")
    start = parse_utc(str(state["campaign_start_time_utc"]))
    deadline = parse_utc(str(state["hard_deadline_utc"]))
    if abs((deadline - start) - 54000.0) > 1e-6:
        raise RuntimeError("persisted start/deadline pair does not span exactly 54,000 seconds")
    return state, deadline


def stop_container(name: str, log: Any) -> None:
    stopped = subprocess.run(
        ["docker", "stop", "--time", "10", name],
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    log.write(f"CAMPAIGN_CONTAINER_STOP name={name} exit={stopped.returncode}\n")
    log.flush()


def run_until_deadline(
    command: Sequence[str],
    *,
    log_path: Path,
    deadline: float,
    docker_name: str | None = None,
    cwd: Path | None = None,
) -> int:
    """Run a subprocess while independently honoring the controller deadline.

    The 20-second safety margin exists only to stop a detached Docker daemon
    workload before the Windows controller terminates its WSL client.  It is
    derived from the same persisted deadline and is not a second budget.
    """

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as log:
        log.write("EXECUTED_COMMAND_JSON=" + json.dumps(list(command)) + "\n")
        log.flush()
        process = subprocess.Popen(
            list(command),
            cwd=str(cwd) if cwd else None,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        while process.poll() is None:
            remaining = deadline - time.time()
            if remaining <= 20.0:
                log.write(f"CAMPAIGN_RUNTIME_CUTOFF remaining_seconds={max(0.0, remaining):.3f}\n")
                log.flush()
                if docker_name:
                    stop_container(docker_name, log)
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=max(1.0, min(10.0, remaining)))
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                while time.time() < deadline:
                    time.sleep(min(0.25, max(0.01, deadline - time.time())))
                raise CampaignCutoff("CAMPAIGN_RUNTIME_CUTOFF")
            time.sleep(min(2.0, max(0.05, remaining - 20.0)))
        return int(process.returncode)


def docker_prefix(*, name: str, writable_root: Path, repo: Path, cpus: int) -> list[str]:
    return [
        "docker", "run", "--rm", "--network", "none", "--platform", "linux/amd64",
        "--name", name, "--cpus", str(cpus), "--memory", "3g",
        "--volume", f"{writable_root}:/campaign-run",
        "--volume", f"{repo}:/repo:ro",
        "--workdir", "/OpenROAD-flow-scripts/flow",
        IMAGE,
    ]


def next_attempt(run_directory: Path) -> tuple[int, Path]:
    run_directory.mkdir(parents=True, exist_ok=True)
    numbers = []
    for path in run_directory.glob("attempt*"):
        match = re.fullmatch(r"attempt(\d+)", path.name)
        if match:
            numbers.append(int(match.group(1)))
    number = max(numbers, default=0) + 1
    attempt = run_directory / f"attempt{number:02d}"
    attempt.mkdir(parents=True, exist_ok=False)
    return number, attempt


def xorshift64star_vectors(count: int = 256, seed: int = 3301) -> list[int]:
    mask = (1 << 64) - 1
    state = seed & mask
    values = []
    for _ in range(count):
        state ^= state >> 12
        state ^= (state << 25) & mask
        state ^= state >> 27
        state &= mask
        values.append((state * 2685821657736338717) & mask)
    return values


def secded_payload_coordinate(payload_bit: int) -> int:
    data_index = 0
    for position in range(1, 72):
        if position & (position - 1):
            if data_index == payload_bit:
                return position - 1
            data_index += 1
    raise ValueError(payload_bit)


def payload_coordinate(architecture: str, payload_bit: int) -> int:
    return payload_bit if architecture == "HSIAO_SECDED" else secded_payload_coordinate(payload_bit)


def workload_definition(operation: str) -> dict[str, Any]:
    faults = 1 if operation == "READ_SINGLE_BIT_ERROR_CORRECT" else 2 if operation == "READ_DOUBLE_BIT_ERROR_DETECT" else 0
    return {
        "schema_version": 1,
        "semantic_operation_class": (
            "READ_SINGLE_PAYLOAD_BIT_ERROR_CORRECT" if faults == 1
            else "READ_TWO_PAYLOAD_BIT_ERROR" if faults == 2
            else operation
        ),
        "rng_seed": 3301,
        "payload_pattern_generator": "xorshift64star(seed=3301,index=i)",
        "payload_generator_exact_definition": (
            "iterative unsigned 64-bit xorshift: x^=x>>12; x^=x<<25; x^=x>>27; "
            "output=x*2685821657736338717 modulo 2^64"
        ),
        "address_sequence": "address[i]=(19+73*i) mod 256",
        "error_injection_sequence": (
            "none" if faults == 0
            else "payload_bit_0=(7*i+3) mod 64" if faults == 1
            else "payload_bit_0=(7*i+3) mod 64; payload_bit_1=(payload_bit_0+7) mod 64"
        ),
        "injected_logical_bits_per_operation": faults,
        "pre_measurement_state_initialization": (
            "one clean read of logical address 19 after reset and before the 16 warm-up cycles"
        ),
        "warm_up_cycles": 16,
        "measured_cycles": 256,
        "exact_operation_count": 256,
    }


def generate_reference_codewords(
    *,
    repo: Path,
    architecture: str,
    evidence: Path,
    deadline: float,
) -> tuple[Path, Path, dict[str, Any]]:
    spec = ARCHITECTURES[architecture]
    payloads = xorshift64star_vectors()
    payload_path = evidence / "workloads/payloads.hex"
    write_text(payload_path, "\n".join(f"{value:016x}" for value in payloads))
    tb_path = evidence / "workloads/reference_encoder_tb.sv"
    codeword_path = evidence / "workloads/codewords_clean.hex"
    executable = evidence / "workloads/reference_encoder.vvp"
    tb = f"""`timescale 1ns/1ps
module reference_encoder_tb;
  reg [63:0] payloads [0:255];
  reg [63:0] data;
  wire [71:0] codeword;
  integer i, output_file;
  {spec['encoder_module']} encoder({spec['encoder_port']});
  initial begin
    $readmemh(\"{payload_path.as_posix()}\", payloads);
    output_file = $fopen(\"{codeword_path.as_posix()}\", \"w\");
    if (output_file == 0) $fatal(1, \"cannot open codeword output\");
    for (i = 0; i < 256; i = i + 1) begin
      data = payloads[i]; #1;
      if (^codeword === 1'bx) $fatal(1, \"unknown reference codeword at %0d\", i);
      $fdisplay(output_file, \"%018h\", codeword);
    end
    $fclose(output_file);
  end
endmodule
"""
    write_text(tb_path, tb)
    compile_command = [
        "iverilog", "-g2012", "-s", "reference_encoder_tb", "-o", str(executable),
        str(tb_path), *[str(repo / item) for item in spec["encoder_sources"]],
    ]
    compile_log = evidence / "workloads/reference_encoder_compile.log"
    if run_until_deadline(compile_command, log_path=compile_log, deadline=deadline) != 0:
        raise RuntimeError("reference encoder compilation failed")
    simulate_command = ["vvp", str(executable)]
    simulate_log = evidence / "workloads/reference_encoder_simulation.log"
    if run_until_deadline(simulate_command, log_path=simulate_log, deadline=deadline) != 0:
        raise RuntimeError("reference encoder simulation failed")
    words = codeword_path.read_text(encoding="utf-8").splitlines()
    if len(words) != 256 or any(re.fullmatch(r"[0-9a-fA-F]{18}", word) is None for word in words):
        raise RuntimeError("reference encoder did not emit 256 known 72-bit codewords")
    return payload_path, codeword_path, {
        "payload_sha256": sha256(payload_path),
        "clean_codeword_sha256": sha256(codeword_path),
        "reference_encoder_tb_sha256": sha256(tb_path),
        "compile_command": compile_command,
        "simulation_command": simulate_command,
    }


def faulted_codeword_file(
    *, architecture: str, operation: str, clean_path: Path, destination: Path
) -> dict[str, Any]:
    words = [int(line, 16) for line in clean_path.read_text(encoding="utf-8").splitlines()]
    injected: list[dict[str, Any]] = []
    if operation in {"READ_SINGLE_BIT_ERROR_CORRECT", "READ_DOUBLE_BIT_ERROR_DETECT"}:
        for index, word in enumerate(words):
            first_payload = (7 * index + 3) % 64
            payload_bits = [first_payload]
            if operation == "READ_DOUBLE_BIT_ERROR_DETECT":
                payload_bits.append((first_payload + 7) % 64)
            coordinates = [payload_coordinate(architecture, bit) for bit in payload_bits]
            for coordinate in coordinates:
                word ^= 1 << coordinate
            words[index] = word
            injected.append(
                {
                    "operation_index": index,
                    "logical_address": (19 + 73 * index) % 256,
                    "payload_bits": payload_bits,
                    "physical_codeword_coordinates": coordinates,
                }
            )
    write_text(destination, "\n".join(f"{word:018x}" for word in words))
    return {
        "path": destination.as_posix(),
        "sha256": sha256(destination),
        "injection_count": len(injected),
        "injections": injected,
    }


def parse_macro_instances(netlist: Path) -> tuple[str, str, dict[str, str]]:
    instances: dict[str, str] = {}
    pattern = re.compile(r"^\s*(sram22_256x(?:64m4w8|8m8w1))\s+(\\?\S+)\s+\(")
    for line in netlist.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(line)
        if match:
            instances[match.group(1)] = match.group(2)
    try:
        data = instances["sram22_256x64m4w8"]
        ecc = instances["sram22_256x8m8w1"]
    except KeyError as exc:
        raise RuntimeError(f"routed netlist lacks expected matched SRAM instance: {exc}") from exc

    def hierarchy(token: str) -> str:
        return f"dut.{token} .mem" if token.startswith("\\") else f"dut.{token}.mem"

    normalized = {kind: token.lstrip("\\") for kind, token in instances.items()}
    return hierarchy(data), hierarchy(ecc), normalized


def ensure_stdcell_model(
    *, repo: Path, deadline: float, evidence: Path
) -> tuple[Path, dict[str, Any]]:
    model_dir = repo / CAMPAIGN_REL / "derived_models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model = model_dir / "sky130_fd_sc_hd__tt_025C_1v80.functional.v"
    log = evidence / "simulation/stdcell_model_generation.log"
    command: list[str] | None = None
    if not model.is_file():
        name = "green_v33_stdcell_model"
        command = [
            "docker", "run", "--rm", "--network", "none", "--platform", "linux/amd64",
            "--name", name, "--cpus", "1", "--memory", "3g",
            "--volume", f"{model_dir}:/campaign-run", IMAGE,
            "yosys", "-Q", "-p",
            (
                f"read_liberty -ignore_miss_func {STDCELL_LIBERTY}; "
                "write_verilog -noattr /campaign-run/sky130_fd_sc_hd__tt_025C_1v80.functional.v"
            ),
        ]
        if run_until_deadline(command, log_path=log, deadline=deadline, docker_name=name) != 0:
            raise RuntimeError("failed to derive functional standard-cell models from pinned Liberty")
    if not model.is_file():
        raise RuntimeError("derived standard-cell model is absent")
    return model, {
        "path": model.relative_to(repo).as_posix(),
        "sha256": sha256(model),
        "source_liberty": STDCELL_LIBERTY,
        "source_liberty_sha256": "ec0e1067a35c8bf20b11e58d1e8ac53326067e4dac84a125cc1b917a3518d0d9",
        "generation_command": command,
        "derivation": "Yosys read_liberty functional import followed by write_verilog",
    }


def gate_testbench(
    *,
    top: str,
    operation: str,
    clock_ns: float,
    payload_path: Path,
    codeword_path: Path,
    vcd_path: Path,
    data_memory: str,
    ecc_memory: str,
) -> str:
    read_mode = operation.startswith("READ_")
    single_mode = operation == "READ_SINGLE_BIT_ERROR_CORRECT"
    double_mode = operation == "READ_DOUBLE_BIT_ERROR_DETECT"
    write_mode = operation == "WRITE_CLEAN"
    idle_mode = operation == "IDLE"
    checks = ""
    if operation in {"READ_CLEAN", "READ_SINGLE_BIT_ERROR_CORRECT"}:
        checks += """
      if (payload_out !== payloads[index]) begin
        $display("FUNCTIONAL_MISMATCH index=%0d expected=%016h actual=%016h", index, payloads[index], payload_out);
        failures = failures + 1;
      end
"""
    if single_mode:
        checks += """
      if (correction_applied !== 1'b1 || detected_uncorrectable !== 1'b0) begin
        $display("SINGLE_ERROR_FLAG_MISMATCH index=%0d corrected=%b uncorrectable=%b", index, correction_applied, detected_uncorrectable);
        failures = failures + 1;
      end
"""
    if double_mode:
        checks += """
      if (detected_uncorrectable !== 1'b1) begin
        $display("DOUBLE_ERROR_FLAG_MISMATCH index=%0d corrected=%b uncorrectable=%b", index, correction_applied, detected_uncorrectable);
        failures = failures + 1;
      end
"""
    ce_value = "1'b0" if idle_mode else "1'b1"
    we_value = "1'b1" if write_mode else "1'b0"
    payload_value = "payloads[index]" if write_mode else "64'b0"
    return f"""`timescale 1ns/1ps
module tb;
  localparam real CLOCK_NS = {clock_ns:.6f};
  reg clk = 1'b0;
  reg rstb = 1'b0;
  reg ce = 1'b0;
  reg we = 1'b0;
  reg [7:0] addr = 8'b0;
  reg [63:0] payload_in = 64'b0;
  wire [63:0] payload_out;
  wire correction_applied;
  wire detected_uncorrectable;
  reg [63:0] payloads [0:255];
  reg [71:0] codewords [0:255];
  integer i, index, address, failures;

  {top} dut(
    .clk(clk), .rstb(rstb), .ce(ce), .we(we), .addr(addr),
    .payload_in(payload_in), .payload_out(payload_out),
    .correction_applied(correction_applied),
    .detected_uncorrectable(detected_uncorrectable)
  );
  always #(CLOCK_NS / 2.0) clk = ~clk;

  task apply_operation;
    input integer requested_index;
    input integer check_result;
    begin
      index = requested_index;
      address = (19 + 73 * index) % 256;
      @(negedge clk);
      addr = address[7:0];
      ce = {ce_value};
      we = {we_value};
      payload_in = {payload_value};
      @(posedge clk); #1;
      if (check_result != 0) begin
{checks.rstrip()}
      end
    end
  endtask

  initial begin
    failures = 0;
    $readmemh("{payload_path.as_posix()}", payloads);
    $readmemh("{codeword_path.as_posix()}", codewords);
    for (i = 0; i < 256; i = i + 1) begin
      address = (19 + 73 * i) % 256;
      {data_memory}[address] = codewords[i][63:0];
      {ecc_memory}[address] = codewords[i][71:64];
    end
    repeat (2) @(posedge clk);
    rstb = 1'b1;
    // Establish a known SRAM output state before every operation-class warm-up.
    // This read is outside both the 16 warm-up operations and measured window.
    @(negedge clk);
    addr = 8'd19;
    ce = 1'b1;
    we = 1'b0;
    payload_in = 64'b0;
    @(posedge clk); #1;
    for (i = 0; i < 16; i = i + 1) apply_operation(i, {1 if read_mode else 0});
    $dumpfile("{vcd_path.as_posix()}");
    $dumpvars(1, dut);
    $display("MEASUREMENT_BEGIN_NS=%.3f", $realtime);
    for (i = 0; i < 256; i = i + 1) apply_operation(i, {1 if read_mode else 0});
    #1;
    $display("MEASUREMENT_END_NS=%.3f", $realtime);
    $dumpoff;
    if (failures != 0) $fatal(1, "FUNCTIONAL_FAILURE_COUNT=%0d", failures);
    $display("SIMULATION_PASS operation={operation} warmup=16 operations=256");
    $finish;
  end
endmodule
"""


def parse_measurement_window(log_path: Path) -> tuple[float, float]:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    begin = re.search(r"MEASUREMENT_BEGIN_NS=([0-9.]+)", text)
    end = re.search(r"MEASUREMENT_END_NS=([0-9.]+)", text)
    if not begin or not end or "SIMULATION_PASS" not in text:
        raise RuntimeError(f"simulation did not emit a valid measured window: {log_path}")
    return float(begin.group(1)), float(end.group(1))


def routed_scalar_activity(vcd_path: Path, *, begin_ns: float, end_ns: float) -> dict[str, dict[str, float]]:
    """Extract toggle density/duty for routed nets directly in ``tb/dut``.

    OpenSTA's native VCD reader in the pinned image resolves the top ports but
    not the routed net names written by ORFS.  The final Verilog and SPEF do
    retain those routed names.  This parser converts only the exact DUT-scope
    VCD signals into explicit ``set_power_activity -density`` records.  Vector
    variables are expanded to the exact ``name[index]`` nets used by ODB;
    child-cell implementation variables and unknown-valued signals are ignored.
    """

    begin_tick = int(round(begin_ns * 1000.0))
    end_tick = int(round(end_ns * 1000.0))
    scope: list[str] = []
    identifiers: dict[str, list[list[str]]] = {}
    widths: dict[str, int] = {}
    in_header = True
    current_tick = 0
    values: dict[tuple[str, int], str] = {}
    last_tick: dict[tuple[str, int], int] = {}
    one_ticks: dict[tuple[str, int], int] = {}
    toggles: dict[tuple[str, int], int] = {}
    known_seen: set[tuple[str, int]] = set()
    with vcd_path.open("r", encoding="utf-8", errors="replace") as stream:
        for raw in stream:
            line = raw.strip()
            if in_header:
                if line.startswith("$scope "):
                    parts = line.split()
                    scope.append(parts[2])
                elif line == "$upscope $end":
                    if scope:
                        scope.pop()
                elif line.startswith("$var ") and scope == ["tb", "dut"]:
                    parts = line.split()
                    if len(parts) >= 6:
                        width = int(parts[2])
                        identifier = parts[3]
                        # A leading backslash is Verilog/VCD escaped-identifier
                        # syntax, not part of the OpenDB net name.
                        reference = parts[4].lstrip("\\")
                        range_match = re.fullmatch(r"\[(-?\d+):(-?\d+)\]", parts[5]) if len(parts) >= 7 else None
                        if width == 1:
                            expanded = [reference]
                        elif range_match:
                            msb, lsb = int(range_match.group(1)), int(range_match.group(2))
                            step = -1 if msb > lsb else 1
                            indices = list(range(msb, lsb + step, step))
                            if len(indices) != width:
                                continue
                            expanded = [f"{reference}[{index}]" for index in indices]
                        else:
                            continue
                        if identifier in widths and widths[identifier] != width:
                            continue
                        widths[identifier] = width
                        identifiers.setdefault(identifier, []).append(expanded)
                elif line == "$enddefinitions $end":
                    in_header = False
                continue
            if not line:
                continue
            if line.startswith("#"):
                current_tick = int(line[1:])
                continue
            if line[0] in "bB":
                parts = line.split(maxsplit=1)
                if len(parts) != 2:
                    continue
                bit_text, identifier = parts[0][1:].lower(), parts[1]
                width = widths.get(identifier)
                if width is None:
                    continue
                if len(bit_text) < width:
                    pad = bit_text[0] if bit_text and bit_text[0] in "xz" else "0"
                    bit_text = pad * (width - len(bit_text)) + bit_text
                bits = list(bit_text[-width:])
            elif line[0] in "01xXzZ":
                identifier = line[1:]
                if widths.get(identifier) != 1:
                    continue
                bits = [line[0].lower()]
            else:
                continue
            if identifier not in identifiers or current_tick < begin_tick:
                continue
            for position, value in enumerate(bits):
                key = (identifier, position)
                if value in {"0", "1"}:
                    known_seen.add(key)
                prior = values.get(key)
                prior_tick = last_tick.get(key, begin_tick)
                interval_end = min(current_tick, end_tick)
                if prior == "1" and interval_end > prior_tick:
                    one_ticks[key] = one_ticks.get(key, 0) + interval_end - prior_tick
                if current_tick <= end_tick and prior in {"0", "1"} and value in {"0", "1"} and prior != value:
                    toggles[key] = toggles.get(key, 0) + 1
                values[key] = value
                last_tick[key] = min(current_tick, end_tick)
    duration_ticks = end_tick - begin_tick
    if duration_ticks <= 0:
        raise RuntimeError("VCD measurement duration must be positive")
    duration_seconds = duration_ticks * 1e-12
    records: dict[str, dict[str, float]] = {}
    for identifier, aliases in identifiers.items():
        for position in range(widths[identifier]):
            key = (identifier, position)
            value = values.get(key)
            if key not in known_seen:
                continue
            tail_start = last_tick.get(key, begin_tick)
            total_one = one_ticks.get(key, 0)
            if value == "1" and end_tick > tail_start:
                total_one += end_tick - tail_start
            record = {
                "toggle_count": float(toggles.get(key, 0)),
                "transition_density_per_second": toggles.get(key, 0) / duration_seconds,
                "duty_fraction": total_one / duration_ticks,
            }
            for names in aliases:
                records[names[position]] = record
    if not records:
        raise RuntimeError("no known scalar routed-net activity was extracted from the DUT VCD scope")
    return records


def net_to_pin_map(netlist: Path) -> dict[str, list[str]]:
    """Map final-Verilog net names to exact OpenSTA instance/pin names."""

    text = netlist.read_text(encoding="utf-8", errors="replace")
    instances = re.compile(
        r"(?ms)^\s*([A-Za-z0-9_$]+)\s+(\\\S+|[^\s(]+)\s+\((.*?)\);"
    )
    connections = re.compile(r"\.([A-Za-z0-9_$]+)\s*\(\s*(\\\S+|[^,()\s]+)\s*\)")
    mapping: dict[str, list[str]] = {}
    for instance_match in instances.finditer(text):
        cell_type, instance, body = instance_match.groups()
        if cell_type in {"module", "input", "output", "wire", "assign"}:
            continue
        instance = instance.lstrip("\\")
        for port, expression in connections.findall(body):
            net = expression.strip().lstrip("\\")
            if re.fullmatch(r"[0-9]+(?:'[bdhoBDHO][0-9a-fA-FxXzZ_]+)?", net):
                continue
            if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*(?:\[-?\d+\])?", net) is None:
                continue
            mapping.setdefault(net, []).append(f"{instance}/{port}")
    return mapping


def write_routed_activity_tcl(
    path: Path,
    records: Mapping[str, Mapping[str, float]],
    *,
    netlist: Path,
) -> dict[str, Any]:
    lines = [
        "# Generated from exact scalar signals in VCD scope tb/dut.",
        "# OpenSTA density input uses the current inverse-time unit (1/ns here).",
        "# Source records retain SI transitions/second; this Tcl applies density_per_second * 1e-9.",
        "set green_v33_annotated_net_count 0",
    ]
    emitted = 0
    skipped = []
    mapped_pin_count = 0
    root_candidate_count = 0
    mapping = net_to_pin_map(netlist)
    for net, activity in sorted(records.items()):
        if "}" in net or "{" in net or "\n" in net:
            skipped.append(net)
            continue
        pins = sorted(set(mapping.get(net, [])))
        if not pins:
            skipped.append(net)
            continue
        pin_list = " ".join(pins)
        density_per_ns = float(activity["transition_density_per_second"]) * 1e-9
        lines.extend(
            [
                (
                    f"if {{[info exists green_v33_activity_roots] && "
                    f"[dict exists $green_v33_activity_roots {{{net}}}]}} {{"
                ),
                (
                    f"  set green_v33_activity_root_port "
                    f"[dict get $green_v33_activity_roots {{{net}}}]"
                ),
                (
                    "  set_power_activity -input_ports $green_v33_activity_root_port "
                    f"-density {density_per_ns:.17g} "
                    f"-duty {float(activity['duty_fraction']):.17g}"
                ),
                "  incr green_v33_activity_root_annotation_count",
                "}",
                # set_power_activity resolves its -pins argument internally with
                # get_pins.  Passing a pre-resolved collection here caused the
                # collection handle to be resolved a second time and silently
                # left these pins with propagated ("input") activity.  Give it
                # the literal routed pin names instead.
                (
                    f"set_power_activity -pins {{{pin_list}}} "
                    f"-density {density_per_ns:.17g} "
                    f"-duty {float(activity['duty_fraction']):.17g}"
                ),
                "incr green_v33_annotated_net_count",
            ]
        )
        emitted += 1
        mapped_pin_count += len(pins)
        if re.match(r"^(?:data|ecc\d*)_dout\[\d+\]$", net):
            root_candidate_count += 1
    lines.append('puts "GREEN_V33_EXPLICIT_ROUTED_NET_ACTIVITY nets=$green_v33_annotated_net_count"')
    write_text(path, "\n".join(lines))
    return {
        "emitted_net_count": emitted,
        "mapped_pin_reference_count": mapped_pin_count,
        "macro_output_activity_root_candidate_count": root_candidate_count,
        "opensta_density_input_unit": "transitions_per_nanosecond",
        "source_density_unit": "transitions_per_second",
        "skipped_net_names": skipped,
        "sha256": sha256(path),
    }


def power_tcl(
    *,
    top: str,
    variant: str,
    operation: str,
    macro_instances: Iterable[str],
    output_path: str | None = None,
    vcd_path: str | None = None,
    routed_activity_tcl_path: str | None = None,
) -> str:
    macro64 = f"/repo/{(MACRO_REL / 'source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib').as_posix()}"
    macro8 = f"/repo/{(MACRO_REL / 'source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib').as_posix()}"
    result = f"/campaign-run/results/sky130hd/{top}/{variant}"
    output = output_path or f"/campaign-run/power/{operation}"
    vcd = vcd_path or f"/campaign-run/activity/{operation}.vcd"
    activity_tcl = routed_activity_tcl_path or f"/campaign-run/activity/{operation}.activity.tcl"
    cells = " ".join(macro_instances)
    return f"""read_liberty {STDCELL_LIBERTY}
read_liberty {macro64}
read_liberty {macro8}
read_db {result}/6_final.odb
set green_v33_activity_roots [dict create]
set green_v33_activity_root_count 0
set green_v33_activity_root_annotation_count 0
set green_v33_block [ord::get_db_block]
foreach green_v33_macro_name {{{cells}}} {{
  set green_v33_macro [$green_v33_block findInst $green_v33_macro_name]
  if {{$green_v33_macro == "NULL"}} {{
    error "GREEN v3.3 activity-root macro not found: $green_v33_macro_name"
  }}
  foreach green_v33_iterm [$green_v33_macro getITerms] {{
    set green_v33_mterm [$green_v33_iterm getMTerm]
    if {{[$green_v33_mterm getIoType] == "OUTPUT"}} {{
      set green_v33_net [$green_v33_iterm getNet]
      if {{$green_v33_net != "NULL"}} {{
        set green_v33_net_name [$green_v33_net getName]
        set green_v33_port_name [format "green_v33_activity_root_%03d" $green_v33_activity_root_count]
        dict set green_v33_activity_roots $green_v33_net_name $green_v33_port_name
        $green_v33_iterm disconnect
        set green_v33_bterm [odb::dbBTerm_create $green_v33_net $green_v33_port_name]
        $green_v33_bterm setSigType SIGNAL
        $green_v33_bterm setIoType INPUT
        incr green_v33_activity_root_count
      }}
    }}
  }}
}}
puts "GREEN_V33_MACRO_OUTPUT_ACTIVITY_ROOTS count=$green_v33_activity_root_count"
read_sdc {result}/6_final.sdc
read_spef {result}/6_final.spef
read_vcd -scope tb/dut {vcd}
source {activity_tcl}
puts "GREEN_V33_MACRO_OUTPUT_ACTIVITY_ROOT_ANNOTATIONS count=$green_v33_activity_root_annotation_count"
report_activity_annotation > {output}/annotation.rpt
report_activity_annotation -report_annotated > {output}/annotated.rpt
report_activity_annotation -report_unannotated > {output}/unannotated.rpt
report_power -digits 12 > {output}/power.rpt
report_power -format json > {output}/power.json
report_power -instances [get_cells {{{cells}}}] -digits 12 > {output}/macros.power.rpt
puts "GREEN_V33_POWER_COMPLETE architecture={top} operation={operation}"
"""


def parse_power_report(path: Path) -> dict[str, dict[str, float]]:
    groups: dict[str, dict[str, float]] = {}
    pattern = re.compile(
        r"^(Sequential|Combinational|Clock|Macro|Pad|Total)\s+"
        r"([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)"
    )
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(line.strip())
        if match:
            groups[match.group(1)] = {
                "internal_w": float(match.group(2)),
                "switching_w": float(match.group(3)),
                "leakage_w": float(match.group(4)),
                "total_w": float(match.group(5)),
            }
    if "Total" not in groups or "Macro" not in groups:
        raise RuntimeError(f"power report lacks Total/Macro rows: {path}")
    return groups


def parse_instances(netlist: Path) -> dict[str, str]:
    instances: dict[str, str] = {}
    pattern = re.compile(r"^\s*([A-Za-z0-9_$]+)\s+(\\?\S+)\s+\(")
    for line in netlist.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(line)
        if match:
            instances[match.group(2).lstrip("\\")] = match.group(1)
    return instances


def classify_cell(cell_type: str | None) -> str:
    if cell_type is None:
        return "top_port_or_unknown"
    lowered = cell_type.lower()
    if lowered.startswith("sram22_"):
        return "macro_interface"
    if any(token in lowered for token in ("__df", "__dl")):
        return "sequential"
    if any(token in lowered for token in ("__clkbuf", "__clkinv")):
        return "clock"
    if any(token in lowered for token in ("__diode", "__fill", "__tap", "__decap")):
        return "physical_only"
    return "combinational"


def annotation_details(path: Path, status: str, instances: Mapping[str, str]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    in_section = False
    heading = "Annotated pins:" if status == "annotated" else "Unannotated pins:"
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip() == heading:
            in_section = True
            continue
        if not in_section or not line.strip():
            continue
        text = line.strip()
        if status == "annotated":
            parts = text.split(maxsplit=1)
            pin = parts[1] if len(parts) == 2 else parts[0]
            source = parts[0] if len(parts) == 2 else "unknown"
        else:
            pin, source = text, "unannotated"
        instance = pin.rsplit("/", 1)[0] if "/" in pin else None
        cell_type = instances.get(instance) if instance else None
        records.append(
            {
                "pin": pin,
                "source": source,
                "instance": instance or "TOP_PORT",
                "cell_type": cell_type or "TOP_PORT_OR_UNKNOWN",
                "classification": classify_cell(cell_type),
            }
        )
    return records


def coverage_report(
    *, annotated_path: Path, unannotated_path: Path, netlist: Path
) -> dict[str, Any]:
    instances = parse_instances(netlist)
    annotated = annotation_details(annotated_path, "annotated", instances)
    unannotated = annotation_details(unannotated_path, "unannotated", instances)
    classes = sorted({row["classification"] for row in annotated + unannotated})
    by_class: dict[str, Any] = {}
    for classification in classes:
        yes = sum(row["classification"] == classification for row in annotated)
        no = sum(row["classification"] == classification for row in unannotated)
        by_class[classification] = {
            "annotated_pin_count": yes,
            "unannotated_pin_count": no,
            "coverage_fraction": yes / (yes + no) if yes + no else None,
        }
    functional_classes = {"combinational", "sequential", "clock"}
    exact_sources = {"vcd", "user", "constant", "clock"}
    yes = sum(
        row["classification"] in functional_classes and row["source"] in exact_sources
        for row in annotated
    )
    inexact = sum(
        row["classification"] in functional_classes and row["source"] not in exact_sources
        for row in annotated
    )
    no = sum(row["classification"] in functional_classes for row in unannotated) + inexact
    source_counts = {
        source: sum(row["source"] == source for row in annotated)
        for source in sorted({row["source"] for row in annotated})
    }
    return {
        "annotated_pin_count": len(annotated),
        "unannotated_pin_count": len(unannotated),
        "aggregate_coverage_fraction": len(annotated) / (len(annotated) + len(unannotated)),
        "by_cell_class": by_class,
        "functional_logic_annotated_pin_count": yes,
        "functional_logic_unannotated_pin_count": no,
        "functional_logic_coverage_fraction": yes / (yes + no) if yes + no else None,
        "annotation_source_counts": source_counts,
        "inexact_propagated_or_default_functional_pin_count": inexact,
        "exact_activity_sources": sorted(exact_sources),
        "macro_internal_activity_coverage": None,
        "macro_activity_boundary": "INTERFACE_PINS_ANNOTATED_INTERNAL_STATE_ACTIVITY_ABSENT",
        "physical_only_pins_excluded_from_functional_logic_coverage": True,
    }


def collect_physical_metrics(results: Path) -> dict[str, Any]:
    finish_path = results.parent.parent.parent.parent / "logs"  # sentinel; replaced below by caller data
    del finish_path
    artifacts = {}
    for name in ("6_final.odb", "6_final.def", "6_final.gds", "6_final.spef", "6_final.sdc", "6_final.v"):
        path = results / name
        if path.is_file():
            artifacts[name] = {"sha256": sha256(path), "size_bytes": path.stat().st_size}
    required = {"6_final.odb", "6_final.gds", "6_final.spef", "6_final.sdc", "6_final.v"}
    if not required.issubset(artifacts):
        raise RuntimeError(f"fresh physical run lacks required final artifacts: {sorted(required - set(artifacts))}")
    return {"artifacts": artifacts}


def preserve_physical_outputs(
    *, attempt_root: Path, results: Path, repo_evidence: Path, top: str, variant: str
) -> None:
    physical = repo_evidence / "physical"
    for name in ("6_final.v", "6_final.spef", "6_final.sdc"):
        copy_preserved(results / name, physical / name)
    logs = attempt_root / "logs/sky130hd" / top / variant
    reports = attempt_root / "reports/sky130hd" / top / variant
    for name in ("1_synth.json", "2_4_floorplan_pdn.json", "5_1_grt.json", "5_2_route.json", "6_report.json"):
        source = logs / name
        if source.is_file():
            copy_preserved(source, physical / name)
    for name in ("synth_stat.txt", "5_global_route.rpt", "5_route_drc.rpt", "6_finish.rpt"):
        source = reports / name
        if source.is_file():
            copy_preserved(source, physical / name)
    for name in ("place-driver.log", "finish-driver.log"):
        source = attempt_root / name
        if source.is_file():
            gzip_preserved(source, physical / f"{name}.gz")


def physical_run(
    *,
    repo: Path,
    architecture: str,
    clock_ns: float,
    seed: int,
    attempt_number: int,
    attempt_root: Path,
    evidence: Path,
    deadline: float,
) -> tuple[Path, dict[str, Any]]:
    spec = ARCHITECTURES[architecture]
    top = str(spec["top"])
    clock_tag = str(clock_ns).replace(".", "p")
    variant = f"clk{clock_tag}ns_seed{seed}"
    config = f"/repo/{(PARENT_REL / 'orfs' / spec['config']).as_posix()}"
    target = f"/campaign-run/results/sky130hd/{top}/{variant}/3_3_place_gp.odb"
    base_make = [
        "make", f"DESIGN_CONFIG={config}", "WORK_HOME=/campaign-run", f"FLOW_VARIANT={variant}",
        f"GPL_RANDOM_SEED={seed}", f"GRT_SEED={seed}", f"OR_SEED={seed}",
        f"CLOCK_PERIOD={clock_ns}", f"ABC_CLOCK_PERIOD_IN_PS={int(clock_ns * 1000)}",
    ]
    commands: dict[str, list[str]] = {}
    place_name = f"green_v33_{architecture.lower()}_s{seed}_a{attempt_number:02d}_place"
    place = [*docker_prefix(name=place_name, writable_root=attempt_root, repo=repo, cpus=3), *base_make, target]
    commands["place"] = place
    place_exit = run_until_deadline(
        place, log_path=attempt_root / "place-driver.log", deadline=deadline, docker_name=place_name
    )
    results = attempt_root / "results/sky130hd" / top / variant
    if place_exit != 0 or not (results / "3_3_place_gp.odb").is_file():
        raise RuntimeError(f"ORFS placement failed with exit {place_exit}")
    shutil.copy2(results / "3_3_place_gp.odb", results / "3_4_place_resized.odb")
    bypass = {
        "id": "UPSTREAM_SRAM22_MAX_TRANSITION_RESIZE_STAGE_BYPASS",
        "applied": True,
        "semantics": (
            "Copied 3_3_place_gp.odb to the 3_4_place_resized.odb handoff. No Liberty, LEF, "
            "GDS, RTL, SDC, or numeric library value was modified; final DRVs remain reported."
        ),
        "compliance_claimed": False,
    }
    finish_name = f"green_v33_{architecture.lower()}_s{seed}_a{attempt_number:02d}_finish"
    finish = [*docker_prefix(name=finish_name, writable_root=attempt_root, repo=repo, cpus=3), *base_make, "finish"]
    commands["finish"] = finish
    finish_exit = run_until_deadline(
        finish, log_path=attempt_root / "finish-driver.log", deadline=deadline, docker_name=finish_name
    )
    if finish_exit != 0:
        raise RuntimeError(f"ORFS finish failed with exit {finish_exit}")
    metrics = collect_physical_metrics(results)
    preserve_physical_outputs(
        attempt_root=attempt_root, results=results, repo_evidence=evidence, top=top, variant=variant
    )
    finish_json = attempt_root / "logs/sky130hd" / top / variant / "6_report.json"
    final_metrics = json.loads(finish_json.read_text(encoding="utf-8")) if finish_json.is_file() else {}
    setup_wns = final_metrics.get("finish__timing__setup__ws")
    route_drc = final_metrics.get("finish__route__drc_errors")
    return results, {
        "top": top,
        "variant": variant,
        "place_exit_code": place_exit,
        "finish_exit_code": finish_exit,
        "commands": commands,
        "documented_exception": bypass,
        "setup_wns_ns": setup_wns,
        "timing_feasible": isinstance(setup_wns, (int, float)) and setup_wns >= 0,
        "finish_route_drc_errors": route_drc,
        **metrics,
    }


def run_activity_and_power(
    *,
    repo: Path,
    architecture: str,
    clock_ns: float,
    seed: int,
    attempt_number: int,
    attempt_root: Path,
    evidence: Path,
    results: Path,
    physical: Mapping[str, Any],
    deadline: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    top = str(physical["top"])
    variant = str(physical["variant"])
    netlist = results / "6_final.v"
    data_memory, ecc_memory, macro_instances = parse_macro_instances(netlist)
    payload_path, clean_codewords, reference = generate_reference_codewords(
        repo=repo, architecture=architecture, evidence=evidence, deadline=deadline
    )
    stdcell_model, stdcell_provenance = ensure_stdcell_model(repo=repo, deadline=deadline, evidence=evidence)
    macro64 = repo / MACRO_REL / "source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.v"
    macro8 = repo / MACRO_REL / "source_checkout/sram22_256x8m8w1/sram22_256x8m8w1.v"
    records: list[dict[str, Any]] = []
    commands: dict[str, Any] = {"reference_encoder": reference}
    for operation in OPERATIONS:
        operation_evidence = evidence / "operations" / operation
        operation_evidence.mkdir(parents=True, exist_ok=True)
        external_activity = attempt_root / "activity"
        external_activity.mkdir(parents=True, exist_ok=True)
        external_power = attempt_root / "power" / operation
        external_power.mkdir(parents=True, exist_ok=True)
        codewords = evidence / "workloads" / f"codewords_{operation.lower()}.hex"
        injection = faulted_codeword_file(
            architecture=architecture, operation=operation, clean_path=clean_codewords, destination=codewords
        )
        vcd = external_activity / f"{operation}.vcd"
        tb = operation_evidence / "gate_activity_tb.sv"
        write_text(
            tb,
            gate_testbench(
                top=top,
                operation=operation,
                clock_ns=clock_ns,
                payload_path=payload_path,
                codeword_path=codewords,
                vcd_path=vcd,
                data_memory=data_memory,
                ecc_memory=ecc_memory,
            ),
        )
        executable = operation_evidence / "gate_activity.vvp"
        compile_command = [
            "iverilog", "-g2012", "-s", "tb", "-o", str(executable),
            str(tb), str(netlist), str(stdcell_model), str(macro64), str(macro8),
        ]
        compile_log = operation_evidence / "iverilog_compile.log"
        if run_until_deadline(compile_command, log_path=compile_log, deadline=deadline) != 0:
            raise RuntimeError(f"routed gate simulation compile failed for {operation}")
        simulation_command = ["vvp", str(executable)]
        simulation_log = operation_evidence / "simulation.log"
        if run_until_deadline(simulation_command, log_path=simulation_log, deadline=deadline) != 0:
            raise RuntimeError(f"routed gate simulation failed for {operation}")
        begin_ns, end_ns = parse_measurement_window(simulation_log)
        if not vcd.is_file() or vcd.stat().st_size == 0:
            raise RuntimeError(f"routed gate simulation produced no VCD for {operation}")
        vcd_hash = sha256(vcd)
        gzip_preserved(vcd, operation_evidence / f"{operation}.vcd.gz")
        scalar_activity = routed_scalar_activity(vcd, begin_ns=begin_ns, end_ns=end_ns)
        activity_tcl = external_activity / f"{operation}.activity.tcl"
        explicit_annotation = write_routed_activity_tcl(activity_tcl, scalar_activity, netlist=netlist)
        copy_preserved(activity_tcl, operation_evidence / "routed_net_activity.tcl")

        tcl = external_power / "power.tcl"
        write_text(
            tcl,
            power_tcl(
                top=top,
                variant=variant,
                operation=operation,
                macro_instances=macro_instances.values(),
            ),
        )
        power_name = f"green_v33_{architecture.lower()}_s{seed}_a{attempt_number:02d}_{operation.lower()}"
        power_command = [
            *docker_prefix(name=power_name, writable_root=attempt_root, repo=repo, cpus=1),
            OPENROAD, "-exit", f"/campaign-run/power/{operation}/power.tcl",
        ]
        power_log = external_power / "openroad.log"
        if run_until_deadline(
            power_command, log_path=power_log, deadline=deadline, docker_name=power_name
        ) != 0:
            raise RuntimeError(f"OpenROAD activity-aware power failed for {operation}")
        for name in (
            "power.tcl", "openroad.log", "annotation.rpt", "annotated.rpt",
            "unannotated.rpt", "power.rpt", "power.json", "macros.power.rpt",
        ):
            source = external_power / name
            if source.is_file():
                copy_preserved(source, operation_evidence / name)
        groups = parse_power_report(external_power / "power.rpt")
        coverage = coverage_report(
            annotated_path=external_power / "annotated.rpt",
            unannotated_path=external_power / "unannotated.rpt",
            netlist=netlist,
        )
        functional_coverage = coverage["functional_logic_coverage_fraction"]
        macro_output_roots = explicit_annotation["macro_output_activity_root_candidate_count"]
        required_macro_output_roots = 72
        timing_feasible = bool(physical.get("timing_feasible"))
        logic_qualified = bool(
            timing_feasible
            and functional_coverage is not None
            and functional_coverage >= 0.95
            and macro_output_roots == required_macro_output_roots
            and vcd_hash
            and physical["artifacts"]["6_final.v"]["sha256"]
            and physical["artifacts"]["6_final.spef"]["sha256"]
        )
        logic = {
            component: groups["Total"][component] - groups["Macro"][component]
            for component in ("internal_w", "switching_w", "leakage_w", "total_w")
        }
        duration_seconds = (end_ns - begin_ns) * 1e-9
        workload = workload_definition(operation)
        workload_hash = canonical_sha256(
            {key: value for key, value in workload.items() if key != "payload_generator_exact_definition"}
        )
        record = {
            "schema_version": 1,
            "record_id": f"{architecture.lower()}_clk{str(clock_ns).replace('.', 'p')}ns_seed{seed}_{operation.lower()}",
            "architecture_id": architecture,
            "physical_seed": seed,
            "clock_period_ns": clock_ns,
            "pvt": {"platform": "sky130hd", "corner": "tt_025C_1v80", "voltage_v": 1.8, "temperature_c": 25},
            "operation_class": operation,
            "workload": workload,
            "workload_sha256": workload_hash,
            "payload_vector_sha256": sha256(payload_path),
            "codeword_vector_sha256": sha256(codewords),
            "fault_injection_manifest": injection,
            "warm_up_cycles": 16,
            "measured_cycles": 256,
            "exact_operation_count": 256,
            "measurement_begin_ns": begin_ns,
            "measurement_end_ns": end_ns,
            "measurement_duration_seconds": duration_seconds,
            "activity": {
                "format": "VCD",
                "sha256": vcd_hash,
                "compressed_preserved_path": (operation_evidence / f"{operation}.vcd.gz").relative_to(repo).as_posix(),
                "external_raw_path": vcd.as_posix(),
                "simulation_tool": "Icarus Verilog",
                "activity_generation_boundary": "POST_ROUTE_GATE_ACTIVITY_ZERO_DELAY_ROUTED_NETLIST",
                "dut_hierarchy": "tb/dut",
                "coverage": coverage,
                "explicit_routed_net_annotation": explicit_annotation,
                "macro_output_activity_root_adapter": {
                    "required_root_count": required_macro_output_roots,
                    "annotated_root_count": macro_output_roots,
                    "all_required_roots_annotated": macro_output_roots == required_macro_output_roots,
                    "odb_mutation_scope": "IN_MEMORY_POWER_ANALYSIS_PROCESS_ONLY",
                    "original_odb_modified": False,
                    "purpose": "Seed VCD-measured SRAM outputs as OpenSTA activity roots for the logic-only boundary",
                },
            },
            "parasitics": {
                "format": "SPEF",
                "sha256": physical["artifacts"]["6_final.spef"]["sha256"],
                "loaded_by_openroad": True,
            },
            "routed_netlist_sha256": physical["artifacts"]["6_final.v"]["sha256"],
            "power": {
                "whole_design_including_partial_macro_w": groups["Total"],
                "macro_reported_partial_w": groups["Macro"],
                "ecc_logic_excluding_macro_w": logic,
                "ecc_logic_energy_j_per_operation": logic["total_w"] * duration_seconds / 256,
                "whole_memory_energy_j_per_operation": None,
                "whole_memory_energy_blocker": "SRAM_MACRO_INTERNAL_ENERGY_INCOMPLETE",
                "report_sha256": sha256(external_power / "power.rpt"),
            },
            "timing_feasible": timing_feasible,
            "qualification_thresholds": {
                "functional_logic_annotation_coverage_minimum": 0.95,
                "required_macro_output_activity_roots": required_macro_output_roots,
            },
            "qualification": (
                "E5_LOGIC_ACTIVITY_QUALIFIED_MACRO_ENERGY_INCOMPLETE"
                if logic_qualified else "E5_BLOCKED_ACTIVITY_COVERAGE_OR_TIMING"
            ),
            "evidence_level": "E5" if logic_qualified else "E4_DIAGNOSTIC",
            "whole_memory_e5_qualified": False,
            "ecc_logic_e5_qualified": logic_qualified,
        }
        write_json(operation_evidence / "E5_RECORD.json", record)
        records.append(record)
        commands[operation] = {
            "compile": compile_command,
            "simulate": simulation_command,
            "power": power_command,
        }
    return records, {
        "macro_instances": macro_instances,
        "standard_cell_model": stdcell_provenance,
        "commands": commands,
    }


def relevant_hashes(repo: Path, architecture: str) -> dict[str, Any]:
    spec = ARCHITECTURES[architecture]
    paths = [
        *(repo / item for item in spec["rtl_sources"]),
        repo / PARENT_REL / "validation/rtl/matched_memory_tops.sv",
        repo / PARENT_REL / "orfs/common.mk",
        repo / PARENT_REL / "orfs" / str(spec["config"]),
        repo / PARENT_REL / "configs/common.sdc",
        repo / PARENT_REL / "orfs/macro_placement_72.tcl",
        repo / PARENT_REL / "orfs/pdn_sram22.tcl",
        repo / PARENT_REL / "orfs/pre_io_placement.tcl",
        repo / MACRO_REL / "source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.lef",
        repo / MACRO_REL / "source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib",
        repo / MACRO_REL / "raw/derived_gds/sram22_256x64m4w8.gds",
        repo / MACRO_REL / "source_checkout/sram22_256x8m8w1/sram22_256x8m8w1.lef",
        repo / MACRO_REL / "source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib",
        repo / MACRO_REL / "raw/derived_gds/sram22_256x8m8w1.gds",
    ]
    return {path.relative_to(repo).as_posix(): sha256(path) for path in paths}


def execute(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    campaign = repo / CAMPAIGN_REL
    runtime_state, deadline = load_deadline(args.runtime_state)
    if time.time() >= deadline:
        raise CampaignCutoff("CAMPAIGN_RUNTIME_CUTOFF")
    clock_tag = str(args.clock_ns).replace(".", "p")
    run_id = f"{args.architecture.lower()}_clk{clock_tag}ns_seed{args.seed}"
    local_run = campaign / "fresh_runs" / run_id
    completion = local_run / "RESULT.json"
    if completion.is_file():
        print(f"GREEN_V33_REUSE run_id={run_id} result={completion}", flush=True)
        return 0
    attempt_number, external_attempt = next_attempt(args.external_root / "fresh_runs" / run_id)
    local_attempt = local_run / f"attempt{attempt_number:02d}"
    local_attempt.mkdir(parents=True, exist_ok=False)
    start = now_utc()
    attempt_record: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "attempt": attempt_number,
        "architecture_id": args.architecture,
        "clock_period_ns": args.clock_ns,
        "seed": args.seed,
        "start_time_utc": start,
        "end_time_utc": None,
        "status": "RUNNING",
        "budget_scope": "ENTIRE_CAMPAIGN",
        "campaign_start_time_utc": runtime_state["campaign_start_time_utc"],
        "hard_deadline_utc": runtime_state["hard_deadline_utc"],
        "campaign_budget_seconds": 54000,
        "per_run_timeout_seconds": None,
        "external_attempt_root": external_attempt.as_posix(),
        "local_evidence_root": local_attempt.relative_to(repo).as_posix(),
    }
    write_json(local_attempt / "ATTEMPT_STATE.json", attempt_record)
    try:
        results, physical = physical_run(
            repo=repo,
            architecture=args.architecture,
            clock_ns=args.clock_ns,
            seed=args.seed,
            attempt_number=attempt_number,
            attempt_root=external_attempt,
            evidence=local_attempt,
            deadline=deadline,
        )
        e5_records, activity_support = run_activity_and_power(
            repo=repo,
            architecture=args.architecture,
            clock_ns=args.clock_ns,
            seed=args.seed,
            attempt_number=attempt_number,
            attempt_root=external_attempt,
            evidence=local_attempt,
            results=results,
            physical=physical,
            deadline=deadline,
        )
        result = {
            **attempt_record,
            "end_time_utc": now_utc(),
            "status": "COMPLETED",
            "fresh_rtl_to_gdsii_executed": True,
            "physical": physical,
            "activity_support": activity_support,
            "operation_records": e5_records,
            "e5_logic_record_count": sum(bool(row["ecc_logic_e5_qualified"]) for row in e5_records),
            "whole_memory_e5_record_count": 0,
            "toolchain": {
                "container_image": IMAGE,
                "orfs_commit": "56496f3980fb6e9e58f10c8aea4a98949c0fe5f2",
                "openroad_commit": "ab6fd26351dc449e69059684dc6aa9ae9046eb36",
                "openroad_version": "26Q3-1080-gab6fd26351",
                "opensta_version": "3.1.0",
                "yosys_version": "0.68+post",
                "simulation_tool": "iverilog/vvp",
            },
            "input_sha256": relevant_hashes(repo, args.architecture),
            "resource_control": {
                "architecture_concurrency": 1,
                "orfs_container_cpus": 3,
                "power_container_cpus": 1,
                "container_memory_limit": "3g",
                "host_execution": "Windows controller -> WSL2 -> pinned Linux container",
            },
        }
        write_json(local_attempt / "ATTEMPT_STATE.json", result)
        write_json(completion, result)
        print(
            f"GREEN_V33_E5_JOB_COMPLETE run_id={run_id} e5_logic_records={result['e5_logic_record_count']}",
            flush=True,
        )
        return 0
    except CampaignCutoff:
        attempt_record.update({"end_time_utc": now_utc(), "status": "CAMPAIGN_RUNTIME_CUTOFF"})
        write_json(local_attempt / "ATTEMPT_STATE.json", attempt_record)
        print(f"CAMPAIGN_RUNTIME_CUTOFF run_id={run_id}", file=sys.stderr, flush=True)
        return 124
    except Exception as exc:
        attempt_record.update(
            {
                "end_time_utc": now_utc(),
                "status": "TOOL_FAILURE",
                "failure_type": type(exc).__name__,
                "failure_message": str(exc),
            }
        )
        write_json(local_attempt / "ATTEMPT_STATE.json", attempt_record)
        print(f"GREEN_V33_E5_JOB_FAILURE run_id={run_id}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--runtime-state", type=Path, required=True)
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--architecture", choices=sorted(ARCHITECTURES), required=True)
    parser.add_argument("--clock-ns", type=float, default=10.0)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    return execute(args)


if __name__ == "__main__":
    raise SystemExit(main())
