"""Reproduce the component coverage partition from immutable Attempt10 reports."""

from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[3]
ATTEMPT10 = (
    REPOSITORY
    / "campaigns"
    / "iscas_sustainability_extension"
    / "memory_compiler"
    / "gate3_attempt10_green_matrix_physical_model_validation"
)
POSTROUTE = ATTEMPT10 / "energy" / "postroute" / "read_dominant"
OUTPUT = HERE / "ACTIVITY_COVERAGE_BY_COMPONENT.csv"

EXPECTED_SHA256 = {
    "U0/annotated.rpt": "e871811d0e639f987c27d4f4c108c67755ecd22d77a07e19d8e9209ca885b0f1",
    "U0/unannotated.rpt": "08143ec30284263baf043f668aac4ef6f965f371efe0c26deeb60c15bb199c9e",
    "E0/annotated.rpt": "1f2385a7cd04112615036596697b65a116735aed53c72fed4fceac31253cc4fb",
    "E0/unannotated.rpt": "c312498e2354e896ac245f7803c44138be2cf5b1e9091b3818caa53954e5f7c8",
}

FIELDS = (
    "architecture_id",
    "workload_id",
    "component_class",
    "count_partition",
    "required_for_power",
    "annotated_pin_count",
    "total_pin_count",
    "coverage_fraction",
    "mapping_status",
    "evidence_class",
    "missing_activity_class",
    "source_id",
)


def _report_lines(architecture: str, report: str) -> list[str]:
    path = POSTROUTE / architecture / "slash_scope" / report
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    key = f"{architecture}/{report}"
    if digest != EXPECTED_SHA256[key]:
        raise RuntimeError(f"immutable source hash mismatch for {path}")
    marker = "Annotated pins:" if report == "annotated.rpt" else "Unannotated pins:"
    lines = path.read_text("utf-8").splitlines()
    start = lines.index(marker) + 1
    return [line.strip().removeprefix("vcd ") for line in lines[start:] if line.strip()]


def _row(
    architecture: str,
    component: str,
    *,
    partition: bool,
    required: bool,
    annotated: int | None,
    total: int | None,
    status: str,
    evidence: str,
    missing: str,
    source: str,
) -> dict[str, object]:
    fraction = ""
    if total:
        assert annotated is not None
        fraction = f"{annotated / total:.6f}"
    return {
        "architecture_id": architecture,
        "workload_id": "read_dominant",
        "component_class": component,
        "count_partition": str(partition).lower(),
        "required_for_power": str(required).lower(),
        "annotated_pin_count": "" if annotated is None else annotated,
        "total_pin_count": "" if total is None else total,
        "coverage_fraction": fraction,
        "mapping_status": status,
        "evidence_class": evidence,
        "missing_activity_class": missing,
        "source_id": source,
    }


def build_rows() -> list[dict[str, object]]:
    u0_annotated = _report_lines("U0", "annotated.rpt")
    u0_unannotated = _report_lines("U0", "unannotated.rpt")
    e0_annotated = _report_lines("E0", "annotated.rpt")
    e0_unannotated = _report_lines("E0", "unannotated.rpt")

    u0_top = sum("/" not in pin for pin in u0_annotated)
    u0_macro = sum(pin.startswith("u_data/") for pin in u0_annotated)
    u0_io = sum(pin.startswith(("input", "output", "hold")) for pin in u0_unannotated)
    u0_wire = len(u0_unannotated) - u0_io

    e0_top = sum("/" not in pin for pin in e0_annotated)
    e0_data = sum(pin.startswith("u_protected_memory.u_data/") for pin in e0_unannotated)
    e0_ecc = sum(pin.startswith("u_protected_memory.u_ecc/") for pin in e0_unannotated)
    e0_antenna = sum(pin.startswith("ANTENNA_") for pin in e0_unannotated)
    e0_io = sum(pin.startswith(("input", "output", "hold")) for pin in e0_unannotated)
    e0_logic = len(e0_unannotated) - e0_data - e0_ecc - e0_antenna - e0_io

    if (u0_top, u0_macro, u0_io, u0_wire) != (148, 148, 310, 2):
        raise RuntimeError("unexpected U0 component partition")
    if (e0_top, e0_data, e0_ecc, e0_antenna, e0_io, e0_logic) != (
        142,
        148,
        36,
        29,
        320,
        2593,
    ):
        raise RuntimeError("unexpected E0 component partition")

    rows = [
        _row("U0", "external_top_ports", partition=True, required=True, annotated=u0_top, total=u0_top, status="MAPPED", evidence="DERIVED", missing="", source="A10_U0_ANNOTATED_LIST"),
        _row("U0", "data_sram_macro_boundary", partition=True, required=True, annotated=u0_macro, total=u0_macro, status="MAPPED", evidence="DERIVED", missing="macro_internal_transistor_activity", source="A10_U0_ANNOTATED_LIST"),
        _row("U0", "io_fix_and_hold_standard_cells", partition=True, required=True, annotated=0, total=u0_io, status="UNANNOTATED", evidence="DERIVED", missing="cell_input_and_output_switching", source="A10_U0_UNANNOTATED_LIST"),
        _row("U0", "inserted_wire_buffer_cell", partition=True, required=True, annotated=0, total=u0_wire, status="UNANNOTATED", evidence="DERIVED", missing="cell_input_and_output_switching", source="A10_U0_UNANNOTATED_LIST"),
        _row("U0", "macro_internal_power_arcs", partition=False, required=False, annotated=None, total=None, status="NOT_STRUCTURALLY_VCD_OBSERVABLE", evidence="NOT_MEASURED", missing="internal_transistor_switching", source="A10_ACTIVITY_MODEL"),
        _row("E0", "external_top_ports", partition=True, required=True, annotated=e0_top, total=e0_top, status="MAPPED", evidence="DERIVED", missing="", source="A10_E0_ANNOTATED_LIST"),
        _row("E0", "data_sram_macro_boundary", partition=True, required=True, annotated=0, total=e0_data, status="UNANNOTATED", evidence="DERIVED", missing="read_write_macro_pin_activity", source="A10_E0_UNANNOTATED_LIST"),
        _row("E0", "ecc_sram_macro_boundary", partition=True, required=True, annotated=0, total=e0_ecc, status="UNANNOTATED", evidence="DERIVED", missing="read_write_macro_pin_activity", source="A10_E0_UNANNOTATED_LIST"),
        _row("E0", "antenna_diode_pins", partition=True, required=False, annotated=0, total=e0_antenna, status="UNANNOTATED", evidence="DERIVED", missing="diode_pin_switching", source="A10_E0_UNANNOTATED_LIST"),
        _row("E0", "io_fix_and_hold_standard_cells", partition=True, required=True, annotated=0, total=e0_io, status="UNANNOTATED", evidence="DERIVED", missing="cell_input_and_output_switching", source="A10_E0_UNANNOTATED_LIST"),
        _row("E0", "flattened_synthesized_logic", partition=True, required=True, annotated=0, total=e0_logic, status="UNANNOTATED_NOT_ATTRIBUTABLE", evidence="DERIVED", missing="glitch_and_internal_logic_switching", source="A10_E0_UNANNOTATED_LIST"),
    ]
    for component, missing in (
        ("ecc_encoder_logic", "encoder_component_attribution"),
        ("ecc_decoder_logic", "decoder_component_attribution"),
        ("clock_network", "clock_and_sequential_pin_activity"),
        ("control_and_interconnect_logic", "component_attribution"),
    ):
        rows.append(_row("E0", component, partition=False, required=True, annotated=None, total=None, status="NOT_SEPARABLE_AFTER_FLATTENING", evidence="NOT_MEASURED", missing=missing, source="A10_E0_FINAL_NETLIST"))
    rows.append(_row("E0", "macro_internal_power_arcs", partition=False, required=False, annotated=None, total=None, status="NOT_STRUCTURALLY_VCD_OBSERVABLE", evidence="NOT_MEASURED", missing="internal_transistor_switching", source="A10_ACTIVITY_MODEL"))
    return rows


def render_csv() -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(build_rows())
    return stream.getvalue()


if __name__ == "__main__":
    OUTPUT.write_text(render_csv(), encoding="utf-8", newline="")
