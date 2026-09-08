"""Attempt10 physical-topology evidence adapter and qualified reliability records.

Default execution audits real macro organization and evaluates logical decoder
controls. Physical reliability is deliberately unavailable without a separately
supplied, source-hashed bitcell/address map. Existing simulator APIs are reused.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import combinations
import json
import math
from pathlib import Path
import re
import sys

from activity_energy import CAMPAIGN, ROOT, PARENT, codec, sha, write_csv, write_json


def proposal_location(mapping: str, address: int, bit: int) -> dict:
    """Explicit bank/address/pin contract. I1/I2 are unimplemented proposals."""
    if mapping not in ("I0", "I1", "I2") or not 0 <= address < 256 or not 0 <= bit < 72:
        raise ValueError("mapping, word address or bit out of range")
    factor = {"I0": 1, "I1": 2, "I2": 4}[mapping]
    local_bit = bit if bit < 64 else bit - 64
    return {"macro_kind": "data" if bit < 64 else "ecc", "bank": local_bit % factor,
            "macro_address": address // factor,
            "macro_data_pin": (local_bit // factor) * factor + address % factor,
            "physical_bitcell_coordinate_um": "NOT_MEASURED"}


def macro_audit(arch: str, seed: int = 11) -> list[dict]:
    final_def = PARENT / f"raw/openroad/work/results/sky130hd/attempt09_{arch.lower()}/seed{seed}/6_final.def"
    text = final_def.read_text(encoding="utf-8")
    dbu = int(re.search(r"UNITS DISTANCE MICRONS (\d+)", text)[1])
    rows = []
    for instance, macro, x, y, orientation in re.findall(r"- (\S+) (sram22_\S+) \+ FIXED \( (\d+) (\d+) \) (\S+) ;", text):
        source = PARENT / "source_checkout" / macro
        lef, spice = source / f"{macro}.lef", source / f"{macro}.spice"
        width, height = map(float, re.search(r"SIZE ([\d.]+) BY ([\d.]+)", lef.read_text()).groups())
        stext = spice.read_text(encoding="utf-8")
        block = re.search(r"\.SUBCKT sp_cell_array .*?\n(.*?)\.ENDS sp_cell_array", stext, re.S)[1]
        cells = re.findall(r"Xcell_(\d+)_(\d+) bl\[(\d+)\] br\[(\d+)\].*?wl\[(\d+)\].*sram_sp_cell_wrapper", block)
        if not cells: raise ValueError("no storage cell connectivity extracted")
        for row, col, bl, br, wl in cells:
            if row != wl or col != bl or col != br: raise ValueError("array instance names disagree with electrical connections")
        rows.append({"architecture_id": arch, "seed": seed, "instance": instance, "macro": macro,
            "macro_origin_um": [int(x) / dbu, int(y) / dbu], "orientation_def": orientation,
            "width_um": width, "height_um": height, "area_um2": width * height,
            "storage_cell_instances": len(cells), "electrical_row_count": len({c[0] for c in cells}),
            "electrical_column_count": len({c[1] for c in cells}),
            "logical_depth": 256, "logical_width": 64 if "256x64" in macro else 8,
            "electrical_to_xy_mapping": "NOT_INDEPENDENTLY_REPRODUCED",
            "address_to_electrical_row_column": "NOT_INDEPENDENTLY_REPRODUCED",
            "classification": "POSTROUTE_MACRO_PLACEMENT_AND_SPICE_CONNECTIVITY_ONLY",
            "source_provenance": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in (final_def, lef, spice)}})
    return rows


def validate_geometry(geometry: dict, *, require_complete: bool = True) -> dict[str, dict]:
    """Fail closed on missing coordinates, duplicate storage identities or provenance.

    Geometry producers must retain GDS instance path/address-decoder correlation.
    A source hash confirms file identity, not silicon or physical LVS correctness.
    """
    if geometry.get("units") != "um" or geometry.get("evidence_level") != "EXTRACTED_BITCELL_ADDRESS_MAP":
        raise ValueError("physical coordinates in um and an extracted address map are required")
    sources = geometry.get("source_provenance", {})
    if not sources or not all(k in geometry for k in ("placement_source", "bitcell_source", "address_mapping_source")):
        raise ValueError("placement, bitcell and address mapping provenance are mandatory")
    for field in ("placement_source", "bitcell_source", "address_mapping_source"):
        if geometry[field] not in sources: raise ValueError(f"unhashed {field}")
    for name, digest in sources.items():
        path = ROOT / name
        if not path.is_file() or sha(path) != digest: raise ValueError(f"stale geometry source: {name}")
    ids, logical = {}, set()
    for cell in geometry.get("cells", []):
        required = ("bitcell_id", "gds_instance_path", "macro_instance", "bank", "word_address", "codeword_bit", "x_um", "y_um")
        if any(k not in cell for k in required): raise ValueError("incomplete storage coordinate")
        identity = (cell["word_address"], cell["codeword_bit"])
        if cell["bitcell_id"] in ids or identity in logical: raise ValueError("non-bijective cell map")
        if not all(isinstance(cell[k], (int, float)) and math.isfinite(cell[k]) for k in ("x_um", "y_um")):
            raise ValueError("nonfinite cell coordinates")
        if not 0 <= cell["word_address"] < 256 or not 0 <= cell["codeword_bit"] < geometry["stored_bits"]:
            raise ValueError("cell identity outside configured memory")
        ids[cell["bitcell_id"]] = cell
        logical.add(identity)
    if not ids or (require_complete and len(ids) != 256 * geometry["stored_bits"]):
        raise ValueError("full memory bitcell coverage is required")
    return ids


def physical_fault_cells(geometry: dict, event: dict) -> list[dict]:
    cells = validate_geometry(geometry)
    if event["shape"] == "explicit_cells":
        names = event["bitcell_ids"]
        if len(set(names)) != len(names): raise ValueError("duplicate upset site")
        try: return [cells[name] for name in names]
        except KeyError as exc: raise ValueError("unknown upset site") from exc
    if event["shape"] == "disk":
        x, y, radius = event["x_um"], event["y_um"], event["radius_um"]
        if radius < 0 or not all(math.isfinite(v) for v in (x, y, radius)): raise ValueError("invalid upset radius")
        return [cell for cell in cells.values() if (cell["x_um"] - x)**2 + (cell["y_um"] - y)**2 <= radius**2]
    raise ValueError("unsupported physical fault geometry")


def outcome(adapter, payload: int, mask: int, architecture: str) -> dict:
    if architecture == "U0":
        return {"outcome": "SDC" if mask else "NO_ERROR", "correction_flag": False,
                "due_flag": False, "payload_matches": mask == 0, "stored_after_scrub": payload ^ mask}
    decoded = adapter.decode(adapter.encode(payload) ^ mask)
    match = decoded.data == payload
    due = decoded.status.value == "DETECTED_UNCORRECTABLE"
    status = "DUE" if due else ("SDC" if not match else ("CORRECTED" if mask else "NO_ERROR"))
    return {"outcome": status, "correction_flag": decoded.status.value == "CORRECTED",
            "due_flag": due, "payload_matches": match,
            "stored_after_scrub": decoded.corrected_codeword_optional}


def map_event(cells: list[dict], adapter, architecture: str) -> list[dict]:
    words = defaultdict(set)
    for cell in cells: words[cell["word_address"]].add(cell["codeword_bit"])
    return [{"word_address": word, "codeword_bit_locations": sorted(bits), "error_multiplicity": len(bits),
             **outcome(adapter, 0x0123456789ABCDEF, sum(1 << b for b in bits), architecture)}
            for word, bits in sorted(words.items())]


def persistent_sequence(adapter, architecture: str, masks: list[int], policy: str, interval: int = 0) -> list[dict]:
    """Functional state control, no radiation-time inference or fabricated rates."""
    if policy not in ("none", "scrub_on_correct", "periodic") or (policy == "periodic" and interval <= 0):
        raise ValueError("invalid scrub policy or interval")
    payload = 0x0123456789ABCDEF
    gold = payload if architecture == "U0" else adapter.encode(payload)
    memory = gold
    records = []
    for cycle, mask in enumerate(masks, 1):
        memory ^= mask
        error_mask = memory ^ gold
        result = outcome(adapter, payload, error_mask, architecture)
        scrub_due = policy == "scrub_on_correct" or (policy == "periodic" and cycle % interval == 0)
        # Model the actual decoder's correction flag, including miscorrection.
        # Never use oracle correctness as a scrub decision.
        writeback = architecture == "E0" and scrub_due and result["correction_flag"]
        if writeback: memory = result["stored_after_scrub"]
        records.append({"step": cycle, "injected_mask_hex": f"{mask:x}", "scrub_writeback": writeback, **result})
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry", type=Path, help="Source-hashed complete physical bitcell map")
    parser.add_argument("--events", type=Path, help="Physical faults in um or explicit bitcell identities")
    args = parser.parse_args()
    if bool(args.geometry) != bool(args.events): raise ValueError("--geometry and --events are required together")
    adapter = codec()
    directory = CAMPAIGN / "interleaving"
    audit = [row for arch in ("U0", "E0") for seed in (11, 13, 17, 19, 23) for row in macro_audit(arch, seed)]
    write_json(directory / "MACRO_ORGANIZATION_AUDIT.json", {"schema_version": 1, "rows": audit})
    configurations, costs = [], []
    base_areas = {arch: sum(r["area_um2"] for r in audit if r["architecture_id"] == arch and r["seed"] == 11) for arch in ("U0", "E0")}
    for mid, factor in (("I0", 1), ("I1", 2), ("I2", 4)):
        configs = {"interleaving_id": mid, "bank_count": factor,
            "status": "EXTERNAL_BASELINE_MAPPING_BITCELL_MAP_UNPROVEN" if mid == "I0" else "EXPLICIT_PHYSICAL_MACRO_BANK_PROPOSAL_NOT_IMPLEMENTED",
            "physical_bit_interleaving_qualified": False,
            "stored_word_mapping": {"data": f"bank = bit % {factor}; macro_address = word // {factor}; din_pin = (bit // {factor}) * {factor} + word % {factor}",
                                    "ecc": "apply same rule to parity bit index (codeword_bit - 64) in the separate ECC macro"},
            "same_capacity": "256 logical payload words x 64 bits; additional macro rows remain unused",
            "word_group_size": factor,
            "macro_count": {"U0": factor, "E0": factor * 2},
            "proposal_floorplan": "retain I0 data/ECC pair; additional identical pairs placed in separate side-by-side bank sites with >=60 um proposed channels; no coordinates assigned before placement",
            "adjacent_bit_mapping": "NOT_QUALIFIED: macro din pin indices do not establish bitcell adjacency; internal column mux m4/m8 must be traced",
            "write_semantics": "existing full-word write" if factor == 1 else "requires read-modify-write or a group buffer because interspersed word bits share SRAM22 byte write masks",
            "read_semantics": "existing synchronous macro read" if factor == 1 else "read all banks at grouped macro address, gather selected word lanes; controller and timing not implemented",
            "minimum_ecc_word_bit_separation_um": "NOT_MEASURED",
            "mapping_examples": [{"word": a, "codeword_bit": b, **proposal_location(mid, a, b)} for a in range(factor) for b in (0, 1, 2, 3, 63, 64, 71)],
            "qualification_requirements": ["address+column-select electrical mapping", "GDS bitcell instance coordinates", "routed wrapper implementing lane transpose and RMW", "matched timing/area/activity/power measurements"]}
        configurations.append(configs)
        for arch in ("U0", "E0"):
            costs.append({"architecture_id": arch, "interleaving_id": mid, "bank_count": factor,
                "macro_count": factor * (2 if arch == "E0" else 1),
                "proposed_macro_area_um2": base_areas[arch] * factor,
                "proposed_additional_macro_area_um2": base_areas[arch] * (factor - 1),
                "macro_area_evidence": "FROZEN_LEF_GEOMETRIC_BUDGET_ONLY" if factor > 1 else "FROZEN_LEF_POSTROUTE_MACRO_COUNT",
                **{name: "NOT_MEASURED" for name in ("ecc_word_bit_separation_um", "routing_cost", "wirelength_um", "area_standard_cell_overhead_um2", "energy_overhead_j", "latency_impact_ns")},
                "physical_implementation_status": configs["status"], "physical_bit_interleaving_qualified": False})
    write_json(directory / "BIT_INTERLEAVING_MAP.json", {"schema_version": 1, "configurations": configurations,
        "scope": "I0 no added external interleaver; this does not imply absent intrinsic SRAM22 column multiplexing",
        "macro_organization_audit": "interleaving/MACRO_ORGANIZATION_AUDIT.json"})
    write_csv(directory / "BIT_INTERLEAVING_PHYSICAL_COST.csv", costs)
    # Logical controls are exhaustive in their stated domains and separately labelled.
    controls = []
    for arch, n in (("U0", 64), ("E0", 72)):
        domains = {"SBU_ALL_COORDINATES": [(b,) for b in range(n)], "DBU_ALL_PAIRS": list(combinations(range(n), 2)),
                   "LOGICAL_CONSECUTIVE_3": [tuple(range(b, b + 3)) for b in range(n - 2)],
                   "LOGICAL_CONSECUTIVE_4": [tuple(range(b, b + 4)) for b in range(n - 3)]}
        for family, patterns in domains.items():
            counts = Counter(outcome(adapter, 0x0123456789ABCDEF, sum(1 << b for b in bits), arch)["outcome"] for bits in patterns)
            controls.append({"architecture_id": arch, "fault_domain": family, "pattern_count": len(patterns), "outcome_counts": dict(counts),
                             "evidence_level": "EXACT_FUNCTIONAL_LOGICAL_COORDINATE_CONTROL", "physical_coverage": "NOT_QUALIFIED",
                             "coverage_denominator": "enumerated logical patterns only, not physical upset events or time"})
    sequence = {arch: {policy: persistent_sequence(adapter, arch, [1, 2, 0, 4], policy, 2) for policy in ("none", "scrub_on_correct", "periodic")}
                for arch in ("U0", "E0")}
    write_json(directory / "LOGICAL_RELIABILITY_CONTROLS.json", {"rows": controls, "persistent_fault_scrub_controls": sequence,
        "scrub_scope": "functional simulator controls; no scrubbing RTL/control energy is added to U0/E0",
        "source_provenance": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in [ROOT / "green_ecc_phy/adapters.py", ROOT / "green_ecc_phy/contracts.py", ROOT / "green_ecc_physical_simulation/registry/codes/hsiao-secded-72-64-v1.json"]}})
    physical_records = []
    if args.geometry:
        geometry = json.loads(args.geometry.read_text())
        validate_geometry(geometry)
        for event in json.loads(args.events.read_text())["events"]:
            cells = physical_fault_cells(geometry, event)
            physical_records.append({"physical_fault": event, "bit_locations": cells,
                "codeword_mapping": map_event(cells, adapter, geometry["architecture_id"]),
                "evidence_level": "GEOMETRY_MAPPED_FUNCTIONAL_ECC_OUTCOME",
                "geometry_sha256": sha(args.geometry), "event_source_sha256": sha(args.events)})
    write_json(directory / "MBU_TO_CODEWORD_MAPPING.json", {"schema_version": 1,
        "classification": "PHYSICAL_TOPOLOGY_MAPPING_INCOMPLETE" if not physical_records else "GEOMETRY_MAPPED_FUNCTIONAL_ECC_OUTCOMES",
        "physical_records": physical_records, "physical_coverage_qualified": False,
        "blocking_evidence": "complete bitcell GDS instance coordinates joined to SRAM22 address/column-select nets and codeword bit identity; calibrated physical upset distribution",
        "do_not_infer": "SPICE row/column names, top-level pin geometry, and software permutations alone are insufficient to map spatial radius to logical errors"})
    rows = []
    for arch in ("U0", "E0"):
        for mapping in ("I0", "I1", "I2"):
            for family in ("SBU", "ADJACENT_DBU", "MBU_RADIUS", "BURST"):
                for policy, interval in (("none", "NOT_APPLICABLE"), ("scrub_on_correct", "NOT_APPLICABLE"), ("periodic", "CONFIGURABLE_NOT_TIME_CALIBRATED")):
                    rows.append({"architecture_id": arch, "interleaving_configuration": mapping, "fault_family": family,
                        "scrub_policy": policy, "scrub_interval": interval, "payload_bits": 64, "stored_bits": 72 if arch == "E0" else 64,
                        "memory_macro_configuration": "256x64 data + 256x8 parity" if arch == "E0" else "256x64 data",
                        **{k: "NOT_QUALIFIED" for k in ("SER", "FIT", "SDC_rate", "DUE_rate", "corrected_error_rate", "uncorrectable_error_rate", "SBU_coverage", "DBU_coverage", "MBU_coverage", "burst_coverage")},
                        "functional_control_reference": "interleaving/LOGICAL_RELIABILITY_CONTROLS.json",
                        "physical_mapping_reference": "interleaving/MBU_TO_CODEWORD_MAPPING.json",
                        "evidence_quality": "LOGICAL_ECC_CONTROLS_WITH_REAL_MACRO_ORGANIZATION; BITCELL_MAP_MISSING",
                        "qualification_status": "NOT_QUALIFIED_PHYSICAL_RELIABILITY",
                        "source_provenance": "Attempt09 final DEF/LEF/SPICE hashes in MACRO_ORGANIZATION_AUDIT.json; unchanged registered Hsiao decoder"})
    write_json(CAMPAIGN / "green_matrix/GREEN_MATRIX_RELIABILITY.json", {"schema_version": 1, "rows": rows,
        "physical_event_results": physical_records, "logical_controls": controls,
        "environment_scaling": {"existing_api": "ser_model.flux_from_location, ser_model.ser_hazucha; qcrit_loader",
            "status": "PRESERVED_NOT_CALIBRATED_FOR_SRAM22", "note": "No per-cell measured Qcrit, sensitive area or physical upset process is supplied; existing technology tables are not substituted for SRAM22 characterization."}})
    write_csv(CAMPAIGN / "green_matrix/GREEN_MATRIX_RELIABILITY.csv", rows)
    (directory / "PHYSICAL_MAPPING_METHOD.md").write_text("""# Physical interleaving and reliability

Classification: PHYSICAL_TOPOLOGY_MAPPING_INCOMPLETE. I0 macro placement is
extracted from each of the five frozen final DEFs and SRAM dimensions from LEF.
SPICE explicitly connects storage instances to electrical wordlines/bitlines:
data = 64 rows x 256 columns, ECC = 32 rows x 64 columns. This is physical memory
organization evidence; it is not a qualified bitcell coordinate/address map.
The data and parity macros use different column multiplexing factors (m4/m8).
I0 means no added external interleaver, not zero intrinsic column multiplexing.

I1/I2 specify two/four physical macro banks and a bijective word-group/bit-lane
transpose. These are implementable architecture contracts, not completed layouts.
They require RMW/group buffering because the data macro has byte write masks.
Their exact extra macro area budgets use unchanged LEF dimensions. Controller
area, routing, latency and energy overhead remain NOT_MEASURED. No improvement
in adjacent-upset coverage is claimed until internal bit placement is joined.

The optional --geometry/--events adapter requires a complete map with word/bit,
bank, macro instance, GDS instance path, x/y in um and source hashes. It rejects
missing/stale provenance, incomplete coverage, duplicate logical bits, unknown
upset sites and invalid radii. A disk or explicit-cell fault maps to cell IDs,
then per-codeword masks, then the repository's existing Hsiao decoder. SDC checks
the returned payload against truth even when correction_applied is asserted.
This creates conditional outcomes; calibrated event probabilities and time are
still required for SER, FIT, SDC/DUE rates and physical coverage fractions.

Logical SBU/all-DBU/consecutive-3/consecutive-4 controls and persistent fault
scrubbing examples are explicitly separate. They are not spatial DBU/MBU tests.
Scrub writeback follows the real correction flag and can preserve a miscorrection;
the model never uses an oracle to decide that hardware should scrub. Periodic
intervals are in functional steps until an access/time model is supplied.

PracticalSRAMSimulator.cpp has index-based adjacent/row/column models; these are
not imported as physical xy geometry. The registered green_ecc_phy decoder is
reused because it identifies the exact frozen Hsiao (72,64) implementation.
Existing latitude/altitude and Qcrit scaling APIs remain unchanged and available;
their empirical defaults do not calibrate this macro's physical upset process.

Original/research-corrected Liberty have identical logic and macro geometry;
no reliability distinction is inferred from a constraint-only diagnostic copy.
Energy/carbon and GREEN rankings remain gated on qualified source evidence.
""", encoding="utf-8")
    print(json.dumps({"macro_audit_rows": len(audit), "reliability_rows": len(rows), "physical_events": len(physical_records), "logical_control_rows": len(controls)}))


if __name__ == "__main__": main()
