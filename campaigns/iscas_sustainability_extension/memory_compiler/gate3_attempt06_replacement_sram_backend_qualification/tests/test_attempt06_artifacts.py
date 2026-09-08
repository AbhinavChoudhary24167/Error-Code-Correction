import hashlib
import json
from pathlib import Path


CAMPAIGN = Path(__file__).resolve().parents[1]
REPO = CAMPAIGN.parents[3]


def load(relative):
    return json.loads((CAMPAIGN / relative).read_text(encoding="utf-8"))


def test_required_view_qualification():
    interface = load("raw/qualification/interface_crosscheck.json")
    timing = load("raw/qualification/timing_view_qualification.json")
    assert interface["overall_result"] == "PASS"
    assert timing["overall_result"] == "QUALIFIED_WITH_PROVENANCE_LIMITATION"
    for macro in ("sram22_256x64m4w8", "sram22_256x8m8w1"):
        assert interface["macros"][macro]["crosscheck"]["result"] == "PASS"
        assert timing["macros"][macro]["corner_count"] == 3


def test_frozen_source_hashes():
    manifest = load("SRAM22_SOURCE_MANIFEST.json")
    assert manifest["upstream_commit"] == "75cbe961e18ee00d5a6c73fa455505f0bcdf4c05"
    for artifact in manifest["artifacts"]:
        path = CAMPAIGN / "source_checkout" / artifact["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]


def test_drc_locality_is_not_misreported_as_signoff():
    locality = load("raw/qualification/drc_locality_analysis.json")
    assert locality["hypothesis_result"] == "SUPPORTED"
    assert locality["qualification_boundary"]["leaf_drc_status"] == "DRC_NOT_INDEPENDENTLY_REPRODUCIBLE"
    assert locality["qualification_boundary"]["prohibited_claim"] == "PHYSICAL_DRC_QUALIFIED"
    assert all(run["sram_internal_fraction"] == 1.0 for run in locality["runs"])


def test_openroad_result_is_partial_for_recorded_reason():
    metrics = load("raw/openroad/integration_metrics.json")
    assert metrics["overall"] == "PARTIAL"
    assert metrics["u0"]["status"] == "DETAIL_ROUTE_NOT_CLEAN"
    assert metrics["e0"]["detailed_route"]["clean"] is True
    assert metrics["e0"]["detailed_route"]["drc_errors"] == 0
    assert Path(CAMPAIGN / metrics["e0"]["finish"]["final_gds"]).is_file()


def test_functional_log_and_policy_boundaries():
    log = (CAMPAIGN / "raw/functional/simulation.log").read_text(encoding="utf-8")
    for marker in (
        "SRAM22_256X64_FUNCTIONAL_PASS",
        "SRAM22_256X8_FUNCTIONAL_PASS",
        "SRAM22_256X72_COMPOSITION_PASS",
        "HSIAO_SECDED_PASS singles=72 doubles=2556",
        "ATTEMPT06_FUNCTIONAL_QUALIFICATION_PASS",
    ):
        assert marker in log
    decision = (CAMPAIGN / "BACKEND_DECISION.md").read_text(encoding="utf-8")
    assert "SRAM22_PARTIALLY_QUALIFIED" in decision
    assert "KEEP_GATE3_FAILED" in decision
    assert "NOT_STARTED_UNAUTHORIZED" in decision
    assert "Attempt07 was not begun" in decision


def test_protected_hsiao_sources_match_registered_baseline():
    expected = {
        "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv": "638b36ff3ab1ee31bb8e29b8d5ea064b5b36d1d7df7a3f2b96c52e305a31e036",
        "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv": "5b232248546e1945ab5084b7f4850851bb62c6e54dc9c4fa00950e2a457590be",
        "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v2_algorithmic_decoder.sv": "3c422dbbddab55e8e2ae141b571e60e63f4ecd87ac409d64b59cc184f21aadcf",
    }
    for relative, digest in expected.items():
        assert hashlib.sha256((REPO / relative).read_bytes()).hexdigest() == digest
