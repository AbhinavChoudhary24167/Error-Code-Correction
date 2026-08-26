from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.gate03er.reproducibility import (
    V1_COMPARATOR_SHA256,
    V1_COMPARISON_SHA256,
    V1_POLICY_SHA256,
    canonicalize_lyt,
    conservative_token_canonicalize,
    compare_runs,
    mapped_master_histogram,
    normalize_log_text,
    normalize_yosys_json,
    validate_policy,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_V1 = ROOT / "scripts/gate03e/reproducibility_policy_v1.json"
COMPARATOR_V1 = ROOT / "scripts/gate03e/reproducibility.py"
POLICY_V2 = ROOT / "scripts/gate03er/reproducibility_policy_v2.json"
CATALOG_V2 = ROOT / "scripts/gate03er/producer_catalog_v2.json"
ADJUDICATION = ROOT / "docs/date2027/rigour_gate_03er/REPRODUCIBILITY_ADJUDICATION.json"


def test_policy_v1_bytes_and_hash_remain_frozen() -> None:
    assert hashlib.sha256(POLICY_V1.read_bytes()).hexdigest() == V1_POLICY_SHA256
    assert hashlib.sha256(COMPARATOR_V1.read_bytes()).hexdigest() == V1_COMPARATOR_SHA256
    assert json.loads(POLICY_V1.read_text())["policy_id"] == "gate03e-reproducibility-v1"


def test_preserved_v1_comparison_hash_and_fail_result_are_unchanged() -> None:
    evidence = json.loads(ADJUDICATION.read_text())
    assert evidence["anchors"]["comparison_v1"]["actual_sha256"] == V1_COMPARISON_SHA256
    assert evidence["anchors"]["comparison_v1"]["expected_sha256"] == V1_COMPARISON_SHA256
    assert evidence["v1_result_preserved"] == {
        "numeric_breach_count": 29,
        "reproducibility_pass": False,
        "semantic_failure_count": 0,
        "unexplained_raw_difference_count": 16,
    }


def test_policy_v2_is_additive_fail_closed_and_has_no_posthoc_exclusions() -> None:
    assert validate_policy(POLICY_V2, CATALOG_V2) == []
    policy = json.loads(POLICY_V2.read_text())
    assert policy["amends"]["preserved_result"] == "FAIL"
    assert policy["anti_posthoc_rules"]["path_specific_exclusion_list"] == []
    assert policy["anti_posthoc_rules"]["unknown_or_unresolved_field"] == "gate failure"


def test_runtime_and_resource_changes_are_recorded_but_not_scientific() -> None:
    first = (
        "[INFO RSZ-0505] Runtime: 3.01s\n"
        "Elapsed time: 0:01.00[h:]min:sec. CPU time: user 1 sys 0 (99%). Peak memory: 123KB.\n"
        "WARNING design area is 12.5\n"
    )
    second = (
        "[INFO RSZ-0505] Runtime: 2.96s\n"
        "Elapsed time: 0:02.00[h:]min:sec. CPU time: user 2 sys 1 (88%). Peak memory: 456KB.\n"
        "WARNING design area is 12.5\n"
    )
    normalized_first, actions = normalize_log_text(first)
    normalized_second, _ = normalize_log_text(second)
    assert normalized_first == normalized_second
    assert "openroad_runtime_message" in actions
    assert "WARNING design area is 12.5" in normalized_first


def test_warning_or_design_transformation_change_remains_a_failure() -> None:
    first, _ = normalize_log_text("Warning: inferred latch\nCreated 22 cells\n")
    second, _ = normalize_log_text("Warning: no latch\nCreated 23 cells\n")
    assert first != second


def test_yosys_summary_masks_observations_but_preserves_pass_identity() -> None:
    first = (
        "End of script. Logfile hash: aaaaa, time: 1.00s, user: 0.5s, system: 0.1s, MEM: 50 MB peak\n"
        "Time spent: 74% 4x read_liberty (0 sec), 7% 4x read_verilog (0 sec), ...\n"
    )
    second = (
        "End of script. Logfile hash: bbbbb, time: 2.00s, user: 1.5s, system: 0.2s, MEM: 80 MB peak\n"
        "Time spent: 73% 4x read_liberty (1 sec), 8% 4x read_verilog (0 sec), ...\n"
    )
    left, _ = normalize_log_text(first)
    right, _ = normalize_log_text(second)
    assert left == right
    changed_pass, _ = normalize_log_text(second.replace("read_verilog", "abc"))
    assert left != changed_pass


def test_klayout_xml_allows_only_the_recognized_lef_run_root() -> None:
    first = b"""<?xml version='1.0'?><technology><dbu>0.001</dbu><reader-options><lefdef><lef-files>/gate03er-run-03/a.lef</lef-files><layer-map>met1:68/20</layer-map><routing>met1</routing><display>visible</display><reader>lefdef</reader></lefdef></reader-options></technology>"""
    second = first.replace(b"/gate03er-run-03", b"/gate03er-run-04")
    left, actions = canonicalize_lyt(first)
    right, _ = canonicalize_lyt(second)
    assert left == right
    assert actions == ["klayout_lef_files_run_root"]
    changed_dbu = second.replace(b"0.001", b"0.002")
    changed_layer = second.replace(b"68/20", b"69/20")
    changed_routing = second.replace(b"<routing>met1", b"<routing>met2")
    changed_display = second.replace(b"visible", b"hidden")
    changed_reader = second.replace(b"lefdef</reader>", b"gds2</reader>")
    assert canonicalize_lyt(changed_dbu)[0] != left
    assert canonicalize_lyt(changed_layer)[0] != left
    assert canonicalize_lyt(changed_routing)[0] != left
    assert canonicalize_lyt(changed_display)[0] != left
    assert canonicalize_lyt(changed_reader)[0] != left


def test_klayout_xml_c14n_normalizes_attribute_order() -> None:
    first = b'<technology><reader-options mode="strict" version="1"><lefdef><lef-files>/gate03er-run-03/a.lef</lef-files></lefdef></reader-options></technology>'
    second = b'<technology><reader-options version="1" mode="strict"><lefdef><lef-files>/gate03er-run-04/a.lef</lef-files></lefdef></reader-options></technology>'
    assert canonicalize_lyt(first)[0] == canonicalize_lyt(second)[0]


def test_semantic_token_canonicalizers_accept_formatting_not_state_changes() -> None:
    left, _ = conservative_token_canonicalize("VERSION 5.8 ;\nDIEAREA ( 0 0 ) ( 10 10 ) ;\n", ".def")
    right, _ = conservative_token_canonicalize("VERSION   5.8; DIEAREA(0 0)(10 10);", ".def")
    assert left == right
    changed, _ = conservative_token_canonicalize("VERSION 5.8; DIEAREA(0 0)(11 10);", ".def")
    assert changed != left

    sdc_1, _ = conservative_token_canonicalize("create_clock -period 1.0 [get_ports clk]\n", ".sdc")
    sdc_2, _ = conservative_token_canonicalize("create_clock  -period  1.0  [ get_ports clk ]", ".sdc")
    assert sdc_1 == sdc_2
    assert conservative_token_canonicalize("create_clock -period 1.1 [get_ports clk]", ".sdc")[0] != sdc_1

    spef_1, _ = conservative_token_canonicalize('*DATE "today"\n*CAP\n1 n 0.25\n', ".spef")
    spef_2, _ = conservative_token_canonicalize('*DATE "tomorrow"\n*CAP 1 n 0.25', ".spef")
    assert spef_1 == spef_2
    assert conservative_token_canonicalize('*DATE "tomorrow"\n*CAP 1 n 0.26', ".spef")[0] != spef_1


def test_yosys_json_canonicalization_is_structural_and_order_independent() -> None:
    left = {"modules": {"top": {"cells": {"u0": {"type": "AND", "connections": {"A": [1], "Y": [2]}}}}}, "creator": "Yosys"}
    reordered = {"creator": "Yosys", "modules": {"top": {"cells": {"u0": {"connections": {"Y": [2], "A": [1]}, "type": "AND"}}}}}
    assert normalize_yosys_json(left) == normalize_yosys_json(reordered)
    changed = json.loads(json.dumps(reordered))
    changed["modules"]["top"]["cells"]["u0"]["connections"]["Y"] = [3]
    assert normalize_yosys_json(left) != normalize_yosys_json(changed)


def test_unknown_qor_field_is_an_unresolved_gate_failure(tmp_path: Path) -> None:
    run_3, run_4 = tmp_path / "run3", tmp_path / "run4"
    relative = Path("logs/sky130hd/gcd/base/metrics.json")
    for root, value in ((run_3, 1), (run_4, 2)):
        (root / relative).parent.mkdir(parents=True)
        (root / relative).write_text(json.dumps({"known": 5, "new_unknown": value}))
    policy_hash = hashlib.sha256(POLICY_V2.read_bytes()).hexdigest()
    artifacts = [
        {"path": relative.as_posix(), "raw_sha256": "a", "canonical_sha256": "a", "normalizations_applied": [], "canonicalization_error": None},
        {"path": "results/sky130hd/gcd/base/6_final.sdc", "raw_sha256": "b", "canonical_sha256": "b", "normalizations_applied": [], "canonicalization_error": None},
        {"path": "objects/sky130hd/gcd/base/klayout.lyt", "raw_sha256": "c", "canonical_sha256": "c", "normalizations_applied": [], "canonicalization_error": None},
    ]
    manifests = []
    for root in (run_3, run_4):
        path = root / "inventory.json"
        path.write_text(json.dumps({"policy_sha256": policy_hash, "run_root": str(root), "artifacts": artifacts}))
        manifests.append(path)
    schema = tmp_path / "schema.json"
    schema.write_text(json.dumps({"metrics": [{"artifact": relative.as_posix(), "path": "known", "gating": True, "absolute_tolerance": 0, "unit": "exact", "family": "preenumerated_other_qor"}]}))
    result = compare_runs(manifests[0], manifests[1], POLICY_V2, schema)
    assert not result["reproducibility_pass"]
    assert result["unknown_metrics"] == [f"{relative.as_posix()}:new_unknown"]


def test_duplicate_schema_and_postfailure_exclusions_are_rejected(tmp_path: Path) -> None:
    policy = json.loads(POLICY_V2.read_text())
    policy["anti_posthoc_rules"]["path_specific_exclusion_list"] = ["failed.metric"]
    bad_policy = tmp_path / "policy.json"
    bad_policy.write_text(json.dumps(policy))
    assert "path-specific exclusion list must remain empty" in validate_policy(bad_policy, CATALOG_V2)

    metric = {"artifact": "logs/a.json", "path": "x", "classification": "scientific QoR/state"}
    schema = tmp_path / "schema.json"
    schema.write_text(json.dumps({"metrics": [metric, metric], "posthoc_exclusions": ["x"], "unknown_metric_rule": "pass"}))
    errors = validate_policy(POLICY_V2, CATALOG_V2, schema)
    assert any("duplicate metric schema entry" in error for error in errors)
    assert "metric schema contains posthoc exclusions" in errors
    assert "metric schema is not fail-closed" in errors


def test_mapped_master_histogram_is_exact(tmp_path: Path) -> None:
    netlist = tmp_path / "mapped.v"
    netlist.write_text(
        "sky130_fd_sc_hd__and2_1 u0 (.A(a));\n"
        "sky130_fd_sc_hd__and2_1 u1 (.A(b));\n"
        "sky130_fd_sc_hd__dfxtp_1 u2 (.D(d));\n",
        encoding="utf-8",
    )
    assert mapped_master_histogram(netlist) == {
        "sky130_fd_sc_hd__and2_1": 2,
        "sky130_fd_sc_hd__dfxtp_1": 1,
    }
