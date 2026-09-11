import hashlib
import json
from pathlib import Path


CAMPAIGN = Path(__file__).resolve().parents[1]
CONFIG_HASH = "dc22607f0f35e401fade14046b8089cfb3f04f9db1db84bb6e24c09f9fb82fd6"


def load(name: str):
    return json.loads((CAMPAIGN / name).read_text(encoding="utf-8"))


def test_control_config_is_frozen():
    payload = (CAMPAIGN / "configs" / "control_8x16_config.py").read_bytes()
    assert len(payload) == 1146
    assert hashlib.sha256(payload).hexdigest() == CONFIG_HASH
    record = load("CONTROL_CONFIG_SHA256.json")
    assert record["byte_identical_throughout_attempt04"] is True
    assert set(
        value
        for key, value in record.items()
        if key.endswith("_sha256")
    ) == {CONFIG_HASH}


def test_verification_result_is_not_overclaimed():
    pre = load("PREPATCH_CONTROL_REPRODUCTION.json")
    post = load("POSTPATCH_CONTROL_VERIFICATION.json")
    status = load("ATTEMPT04_STATUS.json")
    assert pre["drc"]["error_tiles"] == 2140
    assert pre["lvs"]["status"] == "FAIL"
    assert post["drc"]["postpatch_error_tiles"] == 2140
    assert post["lvs"]["postpatch"] == "FAIL"
    assert post["classification"] == "CONTROL_INTEGRATION_REPAIR_FAIL"
    assert status["final_classification"] == "CONTROL_INTEGRATION_REPAIR_FAIL"
    assert status["gate3_state"] == "FAIL"
    assert status["gate4_state"] == "NOT_STARTED_UNAUTHORIZED"


def test_no_masking_or_scope_expansion():
    post = load("POSTPATCH_CONTROL_VERIFICATION.json")
    controls = post["qualification_controls"]
    assert not any(controls.values())
    manifest = load("PATCH_MANIFEST.json")
    assert manifest["installed_openram_modified"] is False
    assert manifest["installed_pdk_modified"] is False
    assert manifest["verification_decks_modified"] is False
    assert manifest["patch_count"] == 10


def test_required_raw_evidence_exists():
    phases = ("prepatch", "p1_lvs_views", "p2_complete_upstream_lvs_fix")
    required = (
        "output_control_8x16/sky130_sram_1rw_8x16_gate3a03_control.gds",
        "output_control_8x16/sky130_sram_1rw_8x16_gate3a03_control.lvs.sp",
        "work_control_8x16/sky130_sram_1rw_8x16_gate3a03_control.ext",
        "work_control_8x16/sky130_sram_1rw_8x16_gate3a03_control.drc.out",
        "work_control_8x16/sky130_sram_1rw_8x16_gate3a03_control.lvs.report",
    )
    for phase in phases:
        for relative in required:
            assert (CAMPAIGN / "raw" / "runs" / phase / relative).is_file()


def test_evidence_manifest_rehashes():
    manifest = load("ATTEMPT04_EVIDENCE_MANIFEST.json")
    assert manifest["algorithm"] == "sha256"
    for row in manifest["files"]:
        path = CAMPAIGN / row["path"]
        assert path.stat().st_size == row["byte_size"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
