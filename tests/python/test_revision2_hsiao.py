import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REV2 = ROOT / "docs/date2027/revision2"
RTL = ROOT / "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v2_algorithmic_decoder.sv"


def test_revision2_seed_protocol_is_predeclared_and_matched():
    env = json.loads((REV2 / "REV2_MULTI_SEED_ENVIRONMENT.json").read_text(encoding="utf-8"))
    assert env["experimental_factor"]["values"] == [11, 13, 17, 19, 23]
    assert env["experimental_factor"]["controls"] == ["GPL_RANDOM_SEED", "GRT_SEED", "OR_SEED"]
    assert env["flow"]["num_cores"] == 1
    assert env["flow"]["synthesis_memory_max_bits"] == 4096


def test_algorithmic_hsiao_columns_match_frozen_identity_without_case_table():
    spec = json.loads((REV2 / "REV2_HSIAO_IDENTITY_SPEC.json").read_text(encoding="utf-8"))
    expected = [int(value, 16) for value in spec["parity_check_matrix"]["columns_hex_in_storage_order"]]
    text = RTL.read_text(encoding="utf-8")
    assignments = re.findall(r"column_match\[(\d+)\]\s*=\s*\(syndrome\s*==\s*8'h([0-9a-fA-F]{2})\)", text)
    actual = [None] * 72
    for index, value in assignments:
        actual[int(index)] = int(value, 16)
    assert actual == expected
    assert len(set(actual)) == 72
    assert all(value and value.bit_count() % 2 == 1 for value in actual)
    code_only = re.sub(r"//.*", "", text)
    assert re.search(r"\bcase\b", code_only, flags=re.IGNORECASE) is None


def test_timing_audit_distinguishes_signed_slack_from_clipped_wns():
    text = (REV2 / "REV2_TIMING_SEMANTICS_AUDIT.md").read_text(encoding="utf-8")
    assert "finish__timing__setup__ws" in text
    assert "finish__timing__fmax" in text
    assert "slack-derived frequency estimate" in text
    assert "achieved Fmax`" in text
