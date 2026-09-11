"""Attempt10 opt-in reproducible RTL activity experiment; never upgrades power evidence.

Run from any directory: python activity_energy.py [--cycles 512]. All writes are
confined to this new campaign. Existing RTL and macro models are read unchanged.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys

CAMPAIGN = Path(__file__).resolve().parents[1]
ROOT = CAMPAIGN.parents[3]
PARENT = CAMPAIGN.parent / "gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"
FAMILIES = ("read_dominant", "write_dominant", "balanced_read_write", "idle_leakage_dominated",
            "ecc_correction_activity", "error_free_normal", "injected_sbu", "injected_dbu_mbu")
sys.path.insert(0, str(ROOT))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v for k, v in row.items()})


def codec():
    from green_ecc_phy.registry import EccRegistry
    return EccRegistry.builtin(ROOT).adapter("hsiao-generated-combinational-72-64-v1")


def initial_payload(addr: int) -> int:
    return ((addr * 0x9E3779B97F4A7C15) ^ 0x0123456789ABCDEF) & ((1 << 64) - 1)


def workload(family: str, cycles: int = 512, seed: int = 11) -> list[dict]:
    if family not in FAMILIES or cycles <= 0:
        raise ValueError("unknown workload or nonpositive cycles")
    rng = random.Random(seed)
    trace = []
    for cycle in range(cycles):
        r = rng.random()
        op = ("IDLE" if family == "idle_leakage_dominated" else
              ("WRITE" if r < {"read_dominant": .1, "write_dominant": .9,
                              "balanced_read_write": .5, "error_free_normal": .3}.get(family, .125) else "READ"))
        addr = rng.randrange(256)
        data = rng.getrandbits(64)
        bits = []
        if op == "READ":
            if family == "ecc_correction_activity" or (family == "injected_sbu" and cycle % 4 == 0):
                bits = [rng.randrange(64)]
            elif family == "injected_dbu_mbu" and cycle % 4 == 0:
                weight = 2 + (cycle // 4) % 3
                start = rng.randrange(65 - weight)
                bits = list(range(start, start + weight))
        trace.append({"cycle": cycle, "operation": op, "address": addr,
                      "payload_hex": f"{data:016x}", "logical_payload_fault_bits": bits})
    return trace


def inspect_vcd(path: Path) -> dict:
    """Count resolved bit transitions, unknown events and DUT scopes, preserving raw file."""
    raw = path.read_text(encoding="utf-8")
    scopes, stack, variables = [], [], {}
    date_free = re.sub(r"\$date.*?\$end", "$date OMITTED_FOR_REPRODUCIBILITY $end", raw, flags=re.S)
    for line in raw.splitlines():
        pieces = line.split()
        if pieces[:1] == ["$scope"]:
            stack.append(pieces[2]); scopes.append(".".join(stack))
        elif pieces[:1] == ["$upscope"]:
            stack.pop()
        elif pieces[:1] == ["$var"]:
            variables.setdefault(pieces[3], {"width": int(pieces[2]), "paths": []})["paths"].append(".".join(stack + [pieces[4]]))
    previous, known_transitions, unknown_events = {}, 0, 0
    last_tick, first_tick = 0, None
    for line in raw.split("$enddefinitions $end", 1)[1].splitlines():
        if not line: continue
        if line.startswith("#"):
            last_tick = int(line[1:])
            if first_tick is None: first_tick = last_tick
            continue
        if line[0] in "bB":
            value, identifier = line[1:].split()
        elif line[0] in "01xXzZ":
            value, identifier = line[0], line[1:]
        else: continue
        if identifier not in variables: continue
        width = variables[identifier]["width"]
        value = value.lower().rjust(width, "0" if value[0] in "01" else value[0])
        if any(c in value for c in "xz"): unknown_events += 1
        if identifier in previous:
            known_transitions += sum(a in "01" and b in "01" and a != b for a, b in zip(value, previous[identifier]))
        previous[identifier] = value
    return {"sha256": sha(path), "date_independent_sha256": hashlib.sha256(date_free.encode()).hexdigest(),
            "timescale": re.search(r"\$timescale\s+(.*?)\s+\$end", raw, re.S)[1],
            "last_timestamp_ticks": last_tick, "unique_variables": len(variables),
            "first_timestamp_ticks": first_tick, "window_ticks": last_tick - first_tick,
            "resolved_bit_transitions": known_transitions, "unknown_value_events": unknown_events,
            "scopes": scopes, "annotation_scope": "tb.dut",
            "scope_check_pass": "tb.dut" in scopes,
            "macro_internal_transistor_activity": "NOT_AVAILABLE_BEHAVIORAL_MODEL"}


def testbench(trace: list[dict], arch: str, adapter) -> str:
    protected = arch == "E0"
    inst = ("e0_sram22_top dut(.clk(clk),.rstb(rstb),.ce(ce),.we(we),.addr(addr),.payload_in(din),"
            ".payload_out(dout),.correction_applied(corr),.detected_uncorrectable(due));" if protected else
            "u0_sram22_top dut(.clk(clk),.rstb(rstb),.ce(ce),.we(we),.addr(addr),.wmask(8'hff),.data_in(din),.data_out(dout));")
    mem = "dut.u_protected_memory.u_data.mem" if protected else "dut.u_data.mem"
    commands = []
    memory = [initial_payload(i) for i in range(256)]
    counts = Counter()
    for row in trace:
        op, addr = row["operation"], row["address"]
        mask = sum(1 << b for b in row["logical_payload_fault_bits"])
        commands.append(f"ce={int(op != 'IDLE')}; we={int(op == 'WRITE')}; addr=8'd{addr}; din=64'h{row['payload_hex']};")
        if mask: commands.append(f"{mem}[{addr}] = {mem}[{addr}] ^ 64'h{mask:016x};")
        commands.append("@(posedge clk); #1;")
        if op == "WRITE": memory[addr] = int(row["payload_hex"], 16)
        if op == "READ":
            result = adapter.decode(adapter.encode(memory[addr]) ^ mask)
            # RTL exposes raw payload even on DUE; the registry adapter returns None.
            expected = (result.data if result.data is not None else memory[addr] ^ mask) if protected else memory[addr] ^ mask
            correction = int(result.status.value == "CORRECTED")
            due = int(result.status.value == "DETECTED_UNCORRECTABLE")
            commands.append(f"if(dout !== 64'h{expected:016x}) $fatal(1, \"payload mismatch cycle {row['cycle']}\");")
            if protected: commands.append(f"if(corr !== 1'b{correction} || due !== 1'b{due}) $fatal(1, \"flags mismatch cycle {row['cycle']}\");")
            counts["corrected_reads"] += correction if protected else 0
            counts["due_reads"] += due if protected else 0
            counts["sdc_reads"] += int(expected != memory[addr] and not (protected and due))
        counts[op.lower()] += 1
        counts["injected_reads"] += bool(mask)
        commands.append("@(negedge clk);")
        if mask: commands.append(f"{mem}[{addr}] = {mem}[{addr}] ^ 64'h{mask:016x};")
    return "\n".join(["`timescale 1ns/1ps", "module tb; reg clk=0; always #5 clk=~clk;",
        "reg rstb=0,ce=0,we=0; reg [7:0] addr=0; reg [63:0] din=0; wire [63:0] dout; wire corr,due; integer i;",
        inst, "initial begin", "repeat(2) @(negedge clk); rstb=1;",
        *[f"ce=1; we=1; addr={i}; din=64'h{initial_payload(i):016x}; @(posedge clk); #1; @(negedge clk);" for i in range(256)],
        "ce=1; we=0; addr=0; @(posedge clk); #1; @(negedge clk);",
        '$dumpfile("activity.vcd"); $dumpvars(0,dut);',
        *commands, '$display("ACTIVITY_PASS ' + json.dumps(dict(counts), sort_keys=True).replace('"', '\\"') + '");',
        "$finish; end endmodule", ""])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=512)
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()
    if not shutil.which("iverilog") or not shutil.which("vvp"):
        raise RuntimeError("Icarus Verilog and vvp are required; no surrogate activity is generated")
    adapter = codec()
    energy = CAMPAIGN / "energy"
    # This Windows Icarus build cannot invoke its own lib/ivl path containing
    # spaces. A campaign-local unchanged copy of that runtime is sufficient.
    iverilog = ["iverilog"]
    ivl_original = Path(shutil.which("iverilog")).parent.parent / "lib" / "ivl"
    if " " in str(ivl_original) and ivl_original.is_dir():
        ivl_copy = energy / "runtime" / "ivl"
        shutil.copytree(ivl_original, ivl_copy, dirs_exist_ok=True)
        iverilog.extend(["-B", str(ivl_copy)])
    sources = sorted((PARENT / "rtl").glob("*.sv"))
    sources += sorted((PARENT / "source_checkout").glob("*/*.v"))
    source_hashes = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in sources}
    results, workloads = [], []
    for family in FAMILIES:
        trace = workload(family, args.cycles, args.seed)
        trace_path = energy / "traces" / f"{family}.json"
        write_json(trace_path, {"seed": args.seed, "cycles": args.cycles, "operations": trace})
        counts = Counter(t["operation"] for t in trace)
        spec = {"workload_id": family, "seed": args.seed, "trace_file": str(trace_path.relative_to(CAMPAIGN)).replace("\\", "/"),
                "trace_sha256": sha(trace_path), "cycles": args.cycles, "clock_period_ns": 10,
                "duration_s": args.cycles * 10e-9, "counts": dict(counts),
                "logical_fault_weight_histogram": dict(Counter(len(t["logical_payload_fault_bits"]) for t in trace if t["logical_payload_fault_bits"])),
                "fault_scope": "TRANSIENT_BEHAVIORAL_STORAGE_BITS_PER_READ_NO_PHYSICAL_GEOMETRY",
                "warmup_excluded": "reset 2 cycles, initialize all 256 addresses, initialize read output",
                "activity": {}}
        for arch in ("U0", "E0"):
            run = energy / "raw" / family / arch
            run.mkdir(parents=True, exist_ok=True)
            tb = run / "tb.sv"
            tb.write_text(testbench(trace, arch, adapter), encoding="utf-8")
            compile_cmd = [*iverilog, "-g2012", "-s", "tb", "-o", "sim.vvp", "tb.sv", *map(str, sources)]
            proc = subprocess.run(compile_cmd, cwd=run, capture_output=True, text=True)
            (run / "compile.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
            if proc.returncode: raise RuntimeError(f"Icarus compile failed: {run}")
            sim = subprocess.run(["vvp", "sim.vvp"], cwd=run, capture_output=True, text=True)
            (run / "simulation.log").write_text(sim.stdout + sim.stderr, encoding="utf-8")
            if sim.returncode or "ACTIVITY_PASS " not in sim.stdout: raise RuntimeError(f"RTL assertion failed: {run}")
            simulation_counts = json.loads(sim.stdout.split("ACTIVITY_PASS ")[1].splitlines()[0])
            for op in ("READ", "WRITE", "IDLE"):
                if simulation_counts.get(op.lower(), 0) != counts.get(op, 0): raise ValueError("operation count mismatch")
            activity = inspect_vcd(run / "activity.vcd")
            if not activity["scope_check_pass"] or activity["unknown_value_events"]: raise ValueError("unusable activity scope or unknowns")
            activity.update({"file": str((run / "activity.vcd").relative_to(CAMPAIGN)).replace("\\", "/"),
                             "simulation_counts": simulation_counts, "testbench_sha256": sha(tb),
                             "compile_command": compile_cmd, "simulation_command": ["vvp", "sim.vvp"]})
            spec["activity"][arch] = activity
            results.append({"architecture_id": arch, "workload_id": family, "workload_seed": args.seed,
                "physical_seed": "NOT_APPLICABLE_RTL_ACTIVITY", "liberty_model": "NOT_APPLICABLE_RTL_ACTIVITY",
                "trace_sha256": sha(trace_path), "activity_sha256": activity["sha256"],
                "read_count": counts.get("READ", 0), "write_count": counts.get("WRITE", 0), "idle_cycles": counts.get("IDLE", 0),
                "duration_s": spec["duration_s"], **simulation_counts,
                **{key: "NOT_QUALIFIED" for key in ("energy_read_j", "energy_write_j", "energy_decode_j", "energy_encode_j", "energy_correct_j", "energy_access_j")},
                **{key: "NOT_MEASURED" for key in ("power_macro_dynamic_w", "power_encoder_w", "power_decoder_w", "power_control_interconnect_w", "power_leakage_w")},
                "activity_evidence_level": "RTL_SIMULATED_BEHAVIORAL_SRAM_MACRO",
                "power_evidence_level": "NOT_MEASURED_FOR_THIS_ACTIVITY",
                "energy_evidence_level": "NOT_QUALIFIED", "power_traceability_complete": False,
                "blocking_evidence": "mapped-net activity annotation coverage, parasitic netlist power attribution, validated SRAM internal-power model"})
        workloads.append(spec)
    if source_hashes != {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in sources}: raise RuntimeError("frozen sources changed during simulation")
    version = subprocess.run([*iverilog, "-V"], capture_output=True, text=True)
    write_json(energy / "WORKLOAD_MANIFEST.json", {"schema_version": 1, "classification": "RTL_ACTIVITY_COMPLETE_ENERGY_NOT_QUALIFIED",
        "python_version": sys.version, "iverilog_version": version.stdout.splitlines()[0], "source_sha256": source_hashes,
        "source_integrity_verified_after_run": True, "workloads": workloads,
        "matched_comparison": "One identical serialized operation/fault trace consumed by both frozen architecture tops; 10 ns clock matches frozen SDC constraint",
        "liberty_distinction": "RTL simulation has no Liberty dependency. Each physical model/seed requires a separate hash-joined power result."})
    write_json(energy / "ENERGY_RESULTS.json", {"schema_version": 1, "rows": results})
    # Different observed counter keys must not silently change the CSV schema.
    keys = list(dict.fromkeys(k for row in results for k in row))
    write_csv(energy / "ENERGY_RESULTS.csv", [{k: row.get(k, 0) for k in keys} for row in results])
    (energy / "ACTIVITY_MODEL.md").write_text("""# Attempt10 activity and energy evidence

Classification: **RTL_ACTIVITY_COMPLETE_ENERGY_NOT_QUALIFIED**.

Eight deterministic workload families run the unchanged Attempt09 U0 and E0 physical
RTL tops against unchanged SRAM22 functional Verilog. Serialized operation traces,
addresses, payloads, clock and data fault masks are identical for each matched pair.
All 256 locations and the read output are initialized before measurement. The
measurement window contains exactly cycles × 10 ns, with initialization excluded.
CE is low in the idle workload but the clock continues toggling; this is not a
clock-gated or pure leakage experiment. Counts and payload/flag checks must pass.
No-error and all read/write operations are checked against the existing registered
Hsiao encoder/decoder. SDC is determined by comparison with the original payload,
not by trusting the correction flag. The idle payload input still toggles, so this
trace measures inactive memory with a live upstream data bus.

Faults flip actual behavioral SRAM mem[] data bits before the read edge and restore
them at the next falling edge. They represent isolated transient storage faults,
not persistent radiation rates or implemented scrubbing. The physical top ties
qualification_fault_mask off; no extra injection XOR hardware is simulated.
The injected DBU/MBU trace uses 2/3/4 logically consecutive payload bits. Physical
adjacency is unproven and is never inferred from Verilog bit numbering.

The VCD includes tb.dut and encoder, decoder and macro-interface signals. SRAM
internal transistors and analog switching are absent from the functional model.
The manifest reports raw and date-independent VCD hashes, unknown events, signal
count, duration, source hashes and observed correction/DUE/SDC read counts.

A seed-11 upstream-original post-route diagnostic has now read matched final ODB,
Liberty, SDC and SPEF artifacts and annotated the read-dominant trace at tb/dut.
Its coverage and tool estimates are recorded in POSTROUTE_ACTIVITY_DIAGNOSTIC.json.
Coverage is only 48.68% for U0 and 4.35% for E0; unmatched pins use default
activity, the VCD is RTL rather than glitch-aware gate activity, and the macro
power model has not been independently validated. The diagnostic therefore does
not qualify energy-per-access or architecture comparisons.

Qualification still requires five seeds for every original/corrected view,
retained annotated/unannotated net lists, and coverage reported separately for
clocks, inputs, sequential outputs, ECC logic and macro boundary/internal power
arcs. RTL-to-gate mapping and inferred/default toggles must be explicit. Sparse
RTL net annotation alone cannot qualify power or glitch energy.

Disjoint power groups are SRAM macro dynamic, ECC encoder, ECC decoder,
control/interconnect dynamic, and leakage. Their sum must equal the total within
declared numerical tolerance; shared nets must not be double counted. A validated
macro internal-power model, including read/write conditions and leakage PVT, is
required. Missing groups remain NOT_MEASURED.

For a measured window T, E_total = integral P(t)dt (or average P × T).
E_access = E_total/(N_read + N_write) only for a nonzero access count; idle energy
is reported as joules/window and leakage power, never divided by zero. Individual
E_read and E_write need isolated/matched measurements or a full-rank operation
mix regression with uncertainty; one aggregate power value cannot identify both.
E_encode and E_decode use attributed encoder/decoder energy and counted valid
operations. E_correct is incremental matched faulty versus clean decoder energy
per actual corrected read; subtract identical idle/background activity. Report
raw workload-average energy separately from these incremental quantities.

No numeric energy or carbon claim is supported by these RTL activity traces alone.
Original Liberty, research-corrected diagnostic Liberty and counterfactual physical
power results must stay separate. Existing postroute default-activity power is
not reused as if it belonged to these workloads. Historical Gate-3 remains FAIL.
""", encoding="utf-8")
    print(json.dumps({"workloads": len(workloads), "simulations": len(results), "classification": "RTL_ACTIVITY_COMPLETE_ENERGY_NOT_QUALIFIED"}))


if __name__ == "__main__":
    main()
