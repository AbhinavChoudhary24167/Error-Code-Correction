import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_source_inventory_is_complete_and_immutable():
    inventory = load("SOURCE_VIEW_INVENTORY.json")
    assert inventory["required_imported_cell_count"] == 29
    assert len(inventory["cells"]) == 29
    assert all(cell["required_by_unchanged_16x8_control"] for cell in inventory["cells"])
    assert all(cell["layout_origin"] == "imported_vendor_hard_cell" for cell in inventory["cells"])
    for cell in inventory["cells"]:
        for view in cell["openram_wrapper_views"].values():
            if view is not None:
                assert len(view["sha256"]) == 64


def test_semantics_block_guessed_materialization():
    semantics = load("ADD_MASK_SEMANTICS.json")
    assert semantics["conclusion"] == "SEMANTICS_NOT_SUCCESSFULLY_ESTABLISHED_FOR_MATERIALIZATION"
    layers = {layer["requested_name"]: layer for layer in semantics["layers"]}
    assert set(layers) == {"CLI1MADD", "CNTMADD", "CP1MADD", "NCM"}
    assert layers["CLI1MADD"]["mapping_confidence"] == "UNKNOWN"
    assert layers["CNTMADD"]["official_local_pdk_name"] == "cfom"
    assert layers["CNTMADD"]["mapping_confidence"] == "UNKNOWN"
    assert layers["CP1MADD"]["mapping_confidence"] == "UNKNOWN"
    assert layers["NCM"]["official_purpose"] == "N-core implant"
    assert layers["NCM"]["mapping_confidence"] == "AUTHORITATIVELY_CONFIRMED"
    assert semantics["transformation_authorized"] is False
    materialized = load("MATERIALIZED_VIEW_MANIFEST.json")
    assert materialized["transformation_performed"] is False
    assert materialized["materialized_views"] == []


def test_leaf_baselines_and_gate():
    matrix = load("LEAF_PREQUALIFICATION_MATRIX.json")
    rows = {row["cell"]: row for row in matrix["cells"]}
    assert matrix["cell_count"] == 29
    assert matrix["qualified_count"] == 2
    colend = rows["sky130_fd_bd_sram__sram_sp_colend"]["direct_vendor_gds_normal_tech"]
    assert colend["drc"]["error_tiles"] == 39
    assert colend["lvs"]["devices"] == {"extracted": 1, "schematic": 1}
    assert colend["lvs"]["status"] == "FAIL"
    colenda = rows["sky130_fd_bd_sram__sram_sp_colenda"]["direct_vendor_gds_normal_tech"]
    assert colenda["drc"]["error_tiles"] == 38
    assert colenda["lvs"]["status"] == "PASS"
    bitcell = rows["sky130_fd_bd_sram__sram_sp_cell_opt1"]["direct_vendor_gds_normal_tech"]
    assert bitcell["drc"]["error_tiles"] == 126
    assert bitcell["lvs"]["devices"] == {"extracted": 8, "schematic": 8}
    assert bitcell["lvs"]["nets"] == {"extracted": 10, "schematic": 9}
    assert bitcell["lvs"]["status"] == "FAIL"
    gate = load("LEAF_QUALIFICATION_GATE.json")
    assert gate["result"] == "FAIL"
    assert gate["required_cell_count"] == 29
    assert gate["qualified_cell_count"] == 2
    assert gate["full_16x8_control_authorized"] is False


def test_control_was_not_run_and_config_is_identical():
    control = load("CONTROL_INTEGRATION_AFTER_LEAF_QUALIFICATION.json")
    assert control["status"] == "NOT_RUN_LEAF_GATE_FAILED"
    assert control["permitted_to_run"] is False
    config = ROOT / control["configuration"]["path"]
    assert hashlib.sha256(config.read_bytes()).hexdigest() == "dc22607f0f35e401fade14046b8089cfb3f04f9db1db84bb6e24c09f9fb82fd6"


def test_generated_pnand2_is_independent_failing_case():
    raw = ROOT / "raw" / "generated_pnand2"
    drc = (raw / "drc.log").read_text(encoding="utf-8", errors="replace")
    report = (raw / "lvs.report").read_text(encoding="utf-8", errors="replace")
    mag = next(raw.glob("*pnand2_0.mag")).read_text(encoding="utf-8", errors="replace")
    assert "COUNT_TOTAL_WITH_HIERARCHICAL_DOUBLE_COUNTING=0" in drc
    assert "Number of devices: 4" in report
    assert "Number of nets: 8 **Mismatch**" in report
    assert "Number of nets: 6 **Mismatch**" in report
    assert "Net: VSUBS" in report
    assert "Netlists do not match." in report
    assert "\nuse " not in "\n" + mag


def test_fresh_integrity_results_are_explicit():
    protected = (ROOT / "raw" / "integrity" / "protected_date_baseline_verify.log").read_text(encoding="utf-8")
    prior = load("raw/integrity/prior_campaign_repository_verification.json")
    assert '"protected_file_count": 7094' in protected
    assert '"status": "PASS"' in protected
    assert prior["status"] == "PASS"
    assert prior["external_attempt02_attempt03"]["status"] == "NOT_REVERIFIED"
