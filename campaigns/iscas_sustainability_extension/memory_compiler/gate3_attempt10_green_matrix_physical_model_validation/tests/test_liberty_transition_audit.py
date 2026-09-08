"""Check physical-model audit evidence and isolation from frozen SRAM constraints."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

import pytest


CAMPAIGN = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("attempt10_liberty_audit", CAMPAIGN / "scripts" / "liberty_transition_audit.py")
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


def load(name):
    return json.loads((CAMPAIGN / "liberty" / name).read_text(encoding="utf-8"))


def test_six_frozen_views_and_characterization_envelopes():
    audit = load("LIBERTY_TRANSITION_MODEL_AUDIT.json")
    expected = {
        ("sram22_256x64m4w8", "tt_025C_1v80"): 3.25762,
        ("sram22_256x64m4w8", "ss_100C_1v60"): 4.86284,
        ("sram22_256x64m4w8", "ff_n40C_1v95"): 2.57436,
        ("sram22_256x8m8w1", "tt_025C_1v80"): 3.25718,
        ("sram22_256x8m8w1", "ss_100C_1v60"): 4.86023,
        ("sram22_256x8m8w1", "ff_n40C_1v95"): 2.57477,
    }
    assert len(audit["views"]) == 6
    assert {(v["library"], v["pvt_view"]): v["research_view_output_bound_ns"] for v in audit["views"]} == expected
    assert audit["historical_attempt09_gate3_status"] == "FAIL"
    for view in audit["views"]:
        original = AUDIT.FROZEN / view["source_relative_to_attempt09"]
        assert AUDIT.sha(original.read_bytes()) == view["source_sha256"]
        assert view["default_max_transition_ns"] == 0.04
        assert view["maximum_characterized_load_pf"] == 0.52
        assert {t["type"] for t in view["output_transition_tables"]} == AUDIT.TRANSITIONS
        for table in view["output_transition_tables"]:
            assert len(table["values_ns"]) == len(table["index_1_ns"]) == 7
            assert all(len(row) == len(table["index_2_pf"]) == 7 for row in table["values_ns"])
            values = [v for row in table["values_ns"] for v in row]
            assert min(values) > 0.04
            assert min(values) == table["minimum_characterized_transition_ns"]
            assert max(values) == table["maximum_characterized_transition_ns"]
            assert table["transition_at_minimum_load_ns"] == [row[0] for row in table["values_ns"]]
            assert table["transition_at_fastest_input_slew_ns"] == table["values_ns"][0]
        rstb, = [p for p in view["pins"] if p["name"] == "rstb"]
        assert rstb["direction"] == "input"
        assert rstb["pin_max_transition_ns"] == 0.351
        assert rstb["capacitance_pf"] > 0
        output_pins = [p for p in view["pins"] if p["direction"] == "output"]
        assert len(output_pins) == (64 if "256x64" in view["library"] else 8)
        assert all(p["pin_max_transition_ns"] is None for p in output_pins)
        assert all(len(p["output_transition_table_ids"]) == 4 for p in output_pins)


def test_transformations_preserve_every_unrelated_byte():
    manifest = load("LIBERTY_TRANSFORMATION_MANIFEST.json")
    assert len(manifest["views"]) == 18
    for view in manifest["views"]:
        original = (AUDIT.FROZEN / view["source_relative_to_attempt09"]).read_bytes()
        result = (CAMPAIGN / "liberty" / view["output_relative_to_liberty"]).read_bytes()
        assert AUDIT.sha(original) == view["source_sha256"]
        assert AUDIT.sha(result) == view["output_sha256"]
        assert AUDIT.apply_edits(original.decode(), view["edits"]).encode() == result
        parsed = AUDIT.parse(result.decode())
        library, = parsed.groups("library")
        pins = [n for n in AUDIT.walk(library) if n.kind == "pin"]
        inputs = [p for p in pins if AUDIT.inherited(p, "direction") == "input"]
        outputs = [p for p in pins if AUDIT.inherited(p, "direction") == "output"]
        assert all(p.attr("max_transition") == "0.351" for p in inputs)
        assert next(p for p in pins if p.name == "rstb").attr("max_transition") == "0.351"
        assert all(p.attr("max_capacitance") == "0.52" for p in outputs)
        if view["model"] == "ORIGINAL":
            assert original == result
            assert not view["edits"]
        elif view["model"] == "CORRECTED":
            assert library.attr("default_max_transition") == "0.04"
            assert len(view["edits"]) == len(outputs)
            assert all(e["kind"] == "ADD_OUTPUT_PIN_MAX_TRANSITION" and not e["original"] for e in view["edits"])
            assert all(float(p.attr("max_transition")) > 2 for p in outputs)
        else:
            assert library.attr("default_max_transition") is None
            assert all(p.attr("max_transition") is None for p in outputs)
            assert len(view["edits"]) == 1
            assert view["edits"][0]["original"] == "default_max_transition : 0.04;"


def test_counterfactual_refuses_to_relax_unprotected_input():
    view = load("LIBERTY_TRANSITION_MODEL_AUDIT.json")["views"][0]
    original = (AUDIT.FROZEN / view["source_relative_to_attempt09"]).read_text()
    tree = AUDIT.parse(original)
    rstb = next(n for n in AUDIT.walk(tree) if n.kind == "pin" and n.name == "rstb")
    entry, = rstb.attrs("max_transition")
    damaged = original[:entry.start] + original[entry.end:]
    with pytest.raises(ValueError, match="non-output constraint"):
        AUDIT.diagnostic_copy(view, damaged, AUDIT.parse(damaged), "PIN_SPECIFIC_OR_NO_GLOBAL_COUNTERFACTUAL")


def test_parser_handles_quoted_braces_comments_and_rejects_truncation():
    text = 'library(foo) { comment : "{ ; } /* quoted */"; /* } */ bus(dout) { direction : output; pin(dout[0]) { max_capacitance : 0.52; } } }'
    library, = AUDIT.parse(text).groups("library")
    assert library.attr("comment") == "{ ; } /* quoted */"
    pin, = library.groups("bus")[0].groups("pin")
    assert pin.name == "dout[0]"
    assert AUDIT.inherited(pin, "direction") == "output"
    with pytest.raises(ValueError, match="Unclosed"):
        AUDIT.parse(text[:-1])


def _check_reproduction(tmp_path):
    AUDIT.main(["--output", str(tmp_path)])
    for expected in (CAMPAIGN / "liberty").glob("LIBERTY_*AUDIT.*"):
        assert (tmp_path / expected.name).read_bytes() == expected.read_bytes()
    manifest = load("LIBERTY_TRANSFORMATION_MANIFEST.json")
    for view in manifest["views"]:
        generated = tmp_path / view["output_relative_to_liberty"]
        assert AUDIT.sha(generated.read_bytes()) == view["output_sha256"]
    AUDIT.main(["--output", str(tmp_path)])
    broken = tmp_path / manifest["views"][0]["output_relative_to_liberty"]
    broken.write_text("deliberately changed artifact")
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        AUDIT.main(["--output", str(tmp_path)])


def test_reproduction_is_deterministic_and_refuses_changed_output():
    # This repository disables pytest's tmpdir plugin in pytest.ini.
    with tempfile.TemporaryDirectory(prefix="liberty_audit_") as temporary:
        _check_reproduction(Path(temporary))
