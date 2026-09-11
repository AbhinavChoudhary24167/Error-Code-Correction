"""Audit frozen SRAM22 Liberty and construct isolated research diagnostic views.

No source file is modified. The small structural Liberty reader retains character
offsets so transformations are insertions/deletions, never a library rewrite.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re

CAMPAIGN = Path(__file__).resolve().parents[1]
FROZEN = CAMPAIGN.parent / "gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"
TRANSITIONS = {"rise_transition", "fall_transition", "retain_rise_slew", "retain_fall_slew"}
MODELS = ("ORIGINAL", "CORRECTED", "PIN_SPECIFIC_OR_NO_GLOBAL_COUNTERFACTUAL")
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*|[^\s(){}:;,"\\]+|[(){}:;,\\]', re.S)
NUMBER = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


@dataclass
class Entry:
    kind: str
    name: str
    start: int
    end: int
    opening: int = -1
    raw: str = ""
    children: list["Entry"] = field(default_factory=list)
    parent: "Entry | None" = field(default=None, repr=False)

    def attrs(self, key):
        return [n for n in self.children if n.kind == key and n.opening < 0]

    def attr(self, key, default=None):
        found = self.attrs(key)
        if len(found) > 1:
            raise ValueError(f"Duplicate {key} in {self.kind}({self.name})")
        return found[0].raw.strip().strip('"') if found else default

    def groups(self, key=None):
        return [n for n in self.children if n.opening >= 0 and (key is None or n.kind == key)]


def parse(text):
    tokens = [m for m in TOKEN.finditer(text) if not m.group().startswith(("/*", "//")) and m.group() != "\\"]
    pos = 0
    root = Entry("root", "", 0, len(text), 0)

    def body(parent, closing=False):
        nonlocal pos
        while pos < len(tokens):
            first = tokens[pos]
            if first.group() == "}":
                if not closing:
                    raise ValueError("Unmatched Liberty closing brace")
                parent.end = first.end()
                pos += 1
                return
            key = first.group()
            pos += 1
            if pos >= len(tokens):
                raise ValueError("Truncated Liberty entry")
            marker = tokens[pos].group()
            if marker == ":":
                value_start = tokens[pos].end()
                pos += 1
                while pos < len(tokens) and tokens[pos].group() != ";":
                    if tokens[pos].group() in ("{", "}"):
                        raise ValueError("Malformed Liberty attribute")
                    pos += 1
                if pos == len(tokens):
                    raise ValueError("Missing attribute semicolon")
                parent.children.append(Entry(key, "", first.start(), tokens[pos].end(), raw=text[value_start:tokens[pos].start()], parent=parent))
                pos += 1
            elif marker == "(":
                start_args = tokens[pos].end()
                pos += 1
                level = 1
                while pos < len(tokens) and level:
                    if tokens[pos].group() == "(":
                        level += 1
                    elif tokens[pos].group() == ")":
                        level -= 1
                    pos += 1
                if level or pos >= len(tokens):
                    raise ValueError("Truncated Liberty arguments")
                args = text[start_args:tokens[pos - 1].start()]
                item = Entry(key, args.strip().strip('"'), first.start(), tokens[pos].end(), raw=args, parent=parent)
                parent.children.append(item)
                if tokens[pos].group() == "{":
                    item.opening = tokens[pos].end()
                    pos += 1
                    body(item, True)
                elif tokens[pos].group() == ";":
                    pos += 1
                else:
                    raise ValueError(f"Unexpected token after {key} arguments")
            else:
                raise ValueError(f"Unsupported Liberty syntax {key} {marker}")
        if closing:
            raise ValueError("Unclosed Liberty group")

    body(root)
    return root


def walk(node):
    yield node
    for child in node.groups():
        yield from walk(child)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def numeric(raw):
    return [float(v) for v in NUMBER.findall(raw)]


def inherited(node, attr):
    while node is not None:
        value = node.attr(attr)
        if value is not None:
            return value
        node = node.parent
    return None


def scalar(node, attr):
    value = node.attr(attr)
    return float(value) if value is not None else None


def table_record(table, templates, text, table_id):
    template = templates[table.name]
    axes = []
    for n in (1, 2):
        local = table.attr(f"index_{n}")
        index = numeric(local if local is not None else template.attr(f"index_{n}", ""))
        if not index or any(a >= b for a, b in zip(index, index[1:])):
            raise ValueError("Missing or unordered characterization axis")
        axes.append(index)
    if (template.attr("variable_1"), template.attr("variable_2")) != ("input_net_transition", "total_output_net_capacitance"):
        raise ValueError("Unexpected transition axes: refusing to infer units")
    values = numeric(table.attr("values", ""))
    if len(values) != len(axes[0]) * len(axes[1]):
        raise ValueError("Transition table shape does not match its indices")
    rows = [values[i:i + len(axes[1])] for i in range(0, len(values), len(axes[1]))]
    container = table.parent.parent
    while container and container.kind not in ("pin", "bus"):
        container = container.parent
    if container is None or inherited(container, "direction") != "output":
        raise ValueError("Transition table is not associated with an output")
    pins = [container] if container.kind == "pin" else container.groups("pin")
    return {
        "table_id": table_id, "type": table.kind, "template": table.name,
        "owner": {"kind": container.kind, "name": container.name},
        "applicable_pins": [p.name for p in pins],
        "related_pin": table.parent.attr("related_pin"),
        "timing_type": table.parent.attr("timing_type"),
        "when": table.parent.attr("when"),
        "variable_1": template.attr("variable_1"), "variable_2": template.attr("variable_2"),
        "index_1_ns": axes[0], "index_2_pf": axes[1], "values_ns": rows,
        "minimum_characterized_transition_ns": min(values),
        "maximum_characterized_transition_ns": max(values),
        "transition_at_minimum_load_ns": [row[0] for row in rows],
        "transition_at_fastest_input_slew_ns": rows[0],
        "transition_at_minimum_load_and_fastest_input_slew_ns": rows[0][0],
        "maximum_characterized_load_pf": max(axes[1]),
        "minimum_characterized_load_pf": min(axes[1]),
        "source_table_sha256": sha(text[table.start:table.end].encode()),
    }


def audit_view(source):
    data = source.read_bytes()
    text = data.decode("utf-8")
    tree = parse(text)
    libraries = tree.groups("library")
    if len(libraries) != 1:
        raise ValueError("Expected exactly one Liberty library")
    library = libraries[0]
    if library.attr("time_unit") != "1ns" or numeric(library.attr("capacitive_load_unit", "")) != [1.0] or "pf" not in library.attr("capacitive_load_unit", ""):
        raise ValueError("Unsupported Liberty units")
    templates = {n.name: n for n in library.groups("lu_table_template")}
    tables = [table_record(n, templates, text, f"table_{i:03d}") for i, n in enumerate(n for n in walk(library) if n.kind in TRANSITIONS)]
    if not tables or {t["type"] for t in tables} != TRANSITIONS:
        raise ValueError("Expected all four supplied output transition table types")
    pins = []
    for pin in (n for n in walk(library) if n.kind == "pin"):
        direction = inherited(pin, "direction")
        pin_tables = [t for t in tables if pin.name in t["applicable_pins"]]
        pin_override = scalar(pin, "max_transition")
        inherited_max = inherited(pin, "max_transition")
        effective = float(inherited_max) if inherited_max is not None else scalar(library, "default_max_transition")
        pins.append({"name": pin.name, "direction": direction,
            "pin_max_transition_ns": pin_override, "effective_max_transition_ns": effective,
            "max_transition_source": "PIN_OR_BUS" if inherited_max is not None else "LIBRARY_DEFAULT",
            "capacitance_pf": scalar(pin, "capacitance"),
            "rise_capacitance_pf": scalar(pin, "rise_capacitance"),
            "fall_capacitance_pf": scalar(pin, "fall_capacitance"),
            "rise_capacitance_range_pf": numeric(pin.attr("rise_capacitance_range", "")),
            "fall_capacitance_range_pf": numeric(pin.attr("fall_capacitance_range", "")),
            "max_capacitance_pf": scalar(pin, "max_capacitance"),
            "output_transition_table_ids": [t["table_id"] for t in pin_tables],
            "research_output_bound_ns": max(t["maximum_characterized_transition_ns"] for t in pin_tables) if pin_tables else None})
    default = scalar(library, "default_max_transition")
    minimum = min(t["minimum_characterized_transition_ns"] for t in tables)
    maximum = max(t["maximum_characterized_transition_ns"] for t in tables)
    source_rel = source.relative_to(FROZEN).as_posix()
    record = {
        "source_relative_to_attempt09": source_rel, "source_sha256": sha(data),
        "library": library.name, "pvt_view": source.stem.removeprefix(library.name + "_"),
        "time_unit": "ns", "capacitance_unit": "pf",
        "default_max_transition_ns": default,
        "minimum_characterized_transition_ns": minimum,
        "maximum_characterized_transition_ns": maximum,
        "maximum_characterized_load_pf": max(t["maximum_characterized_load_pf"] for t in tables),
        "all_output_transition_samples_exceed_default": minimum > default,
        "minimum_to_default_ratio": minimum / default,
        "research_view_output_bound_ns": maximum,
        "pin_count": len(pins), "output_pin_count": sum(p["direction"] == "output" for p in pins),
        "pins": pins, "output_transition_tables": tables,
    }
    return record, text, tree


def apply_edits(text, edits):
    ordered = sorted(edits, key=lambda e: (e["start"], e["end"]))
    if any(a["end"] > b["start"] for a, b in zip(ordered, ordered[1:])):
        raise ValueError("Overlapping edits")
    for edit in reversed(ordered):
        if text[edit["start"]:edit["end"]] != edit["original"]:
            raise ValueError("Edit provenance does not match source")
        text = text[:edit["start"]] + edit["replacement"] + text[edit["end"]:]
    return text


def diagnostic_copy(record, text, tree, model):
    library = tree.groups("library")[0]
    pins = {n.name: n for n in walk(library) if n.kind == "pin"}
    edits = []
    if model == "CORRECTED":
        newline = "\r\n" if "\r\n" in text else "\n"
        for pin in record["pins"]:
            if pin["direction"] != "output":
                continue
            node = pins[pin["name"]]
            if inherited(node, "max_transition") is not None:
                raise ValueError("Existing output limit requires explicit review")
            bound = pin["research_output_bound_ns"]
            if bound is None:
                raise ValueError("Cannot correct output without characterization")
            indent = re.match(r"[ \t]*", text[text.rfind("\n", 0, node.start) + 1:node.start]).group()
            edits.append({"start": node.opening, "end": node.opening, "original": "",
                "replacement": f"{newline}{indent}  max_transition : {bound:.12g};",
                "kind": "ADD_OUTPUT_PIN_MAX_TRANSITION", "pin": node.name, "value_ns": bound})
    elif model == "PIN_SPECIFIC_OR_NO_GLOBAL_COUNTERFACTUAL":
        for pin in record["pins"]:
            if pin["direction"] != "output" and inherited(pins[pin["name"]], "max_transition") is None:
                raise ValueError("Removing default would alter a non-output constraint")
        entry, = library.attrs("default_max_transition")
        edits.append({"start": entry.start, "end": entry.end, "original": text[entry.start:entry.end],
            "replacement": "", "kind": "REMOVE_LIBRARY_DEFAULT_OUTPUT_LIMIT"})
    elif model != "ORIGINAL":
        raise ValueError(f"Unknown model {model}")
    transformed = apply_edits(text, edits)
    reparsed = parse(transformed)
    before_tables = [text[n.start:n.end] for n in walk(tree) if n.kind == "timing" or n.kind == "internal_power"]
    after_tables = [transformed[n.start:n.end] for n in walk(reparsed) if n.kind == "timing" or n.kind == "internal_power"]
    if before_tables != after_tables:
        raise AssertionError("Timing/power group bytes changed")
    original_inputs = [text[n.start:n.end] for n in pins.values() if inherited(n, "direction") != "output"]
    transformed_inputs = [transformed[n.start:n.end] for n in walk(reparsed) if n.kind == "pin" and inherited(n, "direction") != "output"]
    if original_inputs != transformed_inputs:
        raise AssertionError("Non-output pin bytes changed")
    if not any(p["name"] == "rstb" and p["pin_max_transition_ns"] == 0.351 for p in record["pins"]):
        raise AssertionError("Frozen rstb limit differs from expected 0.351 ns")
    return transformed, edits


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=CAMPAIGN / "liberty")
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    sources = sorted((FROZEN / "source_checkout").glob("sram22_*/*.lib"))
    if len(sources) != 6:
        raise ValueError(f"Expected exactly six frozen views, found {len(sources)}")
    views = []
    manifests = []
    for source in sources:
        record, text, tree = audit_view(source)
        views.append(record)
        for model in MODELS:
            output = args.output / model / source.parent.name / source.name
            output.parent.mkdir(parents=True, exist_ok=True)
            result, edits = diagnostic_copy(record, text, tree, model)
            encoded = result.encode("utf-8")
            if output.exists() and output.read_bytes() != encoded:
                raise ValueError(f"Refusing to overwrite differing generated artifact: {output}")
            output.write_bytes(encoded)
            manifests.append({"model": model, "source_relative_to_attempt09": record["source_relative_to_attempt09"],
                "source_sha256": record["source_sha256"], "output_relative_to_liberty": output.relative_to(args.output).as_posix(),
                "output_sha256": sha(encoded), "edits": edits,
                "timing_and_internal_power_groups_byte_identical": True,
                "non_output_pins_byte_identical": True, "rstb_max_transition_ns": 0.351,
                "foundry_validated": False, "production_source_modified": False})
        if sha(source.read_bytes()) != record["source_sha256"]:
            raise AssertionError("Frozen source changed while auditing")
    audit = {
        "schema_version": "1.0.0", "classification": "UPSTREAM_SRAM22_OUTPUT_MAX_TRANSITION_MODEL_INCONSISTENCY",
        "qualification": "PROVENANCE_LIMITED_NOT_EXTERNAL_INTEGRATION_DRV",
        "historical_attempt09_gate3_status": "FAIL", "historical_attempt09_reassessment": "KEEP_GATE3_FAILED",
        "view_count": len(views), "views": views,
        "correction_method": {
            "label": "RESEARCH_CORRECTED_DIAGNOSTIC_LIBERTY",
            "rule": "For each output pin and PVT view, set a pin-specific max_transition to the maximum supplied rise_transition, fall_transition, retain_rise_slew, or retain_fall_slew sample applicable to that pin.",
            "rounding": "No upward margin; original numeric precision retained.",
            "interpretation": "Characterization-envelope diagnostic bound, not a demonstrated safe operating limit or newly characterized Liberty.",
            "scope": "Only the supplied input-slew/load table domain; no justification for extrapolated loads/slews or receiver constraints.",
            "preserved": ["global default_max_transition 0.04 in CORRECTED", "all input constraints including rstb 0.351 ns", "all timing and power tables", "output max_capacitance", "all other source bytes"],
            "counterfactual_rule": "Remove the global default only after verifying every non-output signal pin has its own or inherited explicit max_transition.",
            "foundry_validated": False,
        },
        "limits": ["No SPICE characterization regenerated", "No foundry/signoff validation", "Audit alone establishes no physical PPA, energy, reliability, carbon, or GREEN ranking effect", "Independent SRAM input rstb requirement remains unchanged"],
    }
    write_json(args.output / "LIBERTY_TRANSITION_MODEL_AUDIT.json", audit)
    write_json(args.output / "LIBERTY_TRANSFORMATION_MANIFEST.json", {
        "schema_version": "1.0.0", "generator_relative_to_campaign": "scripts/liberty_transition_audit.py",
        "generator_sha256": sha(Path(__file__).read_bytes()), "views": manifests,
        "offset_units": "Unicode character offsets in UTF-8-decoded frozen source; frozen sources are ASCII",
        "invariant": "Every output is exactly its frozen input with only listed offset edits; ORIGINAL is byte-identical.",
    })
    rows = ["# Frozen SRAM22 output-transition audit", "",
        "Classification: **UPSTREAM_SRAM22_OUTPUT_MAX_TRANSITION_MODEL_INCONSISTENCY**.", "",
        "Attempt09 remains **FAIL / KEEP_GATE3_FAILED**. Its residual data-rstb failure is independent of the output-model discrepancy.", "",
        "| Macro | PVT | Default (ns) | Table minimum (ns) | Table maximum / diagnostic bound (ns) | Max load (pF) | Outputs |",
        "|---|---|---:|---:|---:|---:|---:|"]
    for v in views:
        rows.append(f"| {v['library']} | {v['pvt_view']} | {v['default_max_transition_ns']:g} | {v['minimum_characterized_transition_ns']:g} | {v['maximum_characterized_transition_ns']:g} | {v['maximum_characterized_load_pf']:g} | {v['output_pin_count']} |")
    rows += ["", "All samples of all four supplied output-transition table types exceed the 0.04 ns global default in every frozen view. The JSON records full axes and tables, min-load columns, fastest-input rows, applicable pins, input capacitance, explicit/effective pin limits, and source hashes.", "",
        "## Diagnostic bound and its limits", "",
        "CORRECTED adds an explicit limit to each output pin equal to the largest supplied output-transition sample for that pin in that PVT view, across rise, fall, and retention slew tables. It preserves the upstream global attribute and every non-output constraint. The envelope admits all supplied characterization grid samples without selecting an arbitrary target such as 0.4 ns. It is a research-corrected characterization-consistent diagnostic view, **not a foundry correction or a demonstrated safe operating limit**. Output receivers retain their separate Liberty limits; output loads and input slews must still be checked against characterization axes. Values outside that domain are not qualified by this bound.", "",
        "ORIGINAL is byte-identical to frozen source. PIN_SPECIFIC_OR_NO_GLOBAL_COUNTERFACTUAL removes only the global default after verifying explicit limits protect every non-output signal pin. In all views rstb remains **0.351 ns**. Complete timing/internal-power groups and non-output pin groups are byte-identical, and manifests list every exact insertion/deletion. GDS/LEF/RTL/SDC are not altered by this generator.", "",
        "## Research consequences", "",
        "The audit proves an inconsistency between a library-wide output constraint and its supplied transition samples. It does not prove that the default is a typo, reconstruct its intended value, waive an input requirement, or regenerate characterization. Full matched physical runs must distinguish optimization/PPA effects from report classification changes. No PPA, energy, reliability, carbon, or GREEN ranking improvement follows from this audit alone.", "",
        "Reproduce from the repository root with `python campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation/scripts/liberty_transition_audit.py`. The generator refuses to overwrite a differing generated Liberty. All source inputs are read from frozen Attempt09/source_checkout.", ""]
    (args.output / "LIBERTY_TRANSITION_MODEL_AUDIT.md").write_text("\n".join(rows), encoding="utf-8")
    print(json.dumps({"views_audited": len(views), "diagnostic_files": len(manifests), "bounds_ns": {v['library'] + ':' + v['pvt_view']: v['research_view_output_bound_ns'] for v in views}}, sort_keys=True))


if __name__ == "__main__":
    main()
