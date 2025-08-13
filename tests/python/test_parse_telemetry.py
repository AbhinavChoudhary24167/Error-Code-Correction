from pathlib import Path
import json

import pandas as pd
import pytest

import parse_telemetry

_VALID_ROW = (
    "workload_id,node_nm,vdd,tempC,clk_MHz,xor_toggles,and_toggles,add_toggles,"
    "corr_events,words,accesses,scrub_s,capacity_gib,runtime_s\n"
    "wl,16,0.8,25,1000,10,5,2,1,1024,2048,3600,1.0,7200\n"
)


def test_round_trip(tmp_path: Path) -> None:
    csv_in = tmp_path / "in.csv"
    csv_in.write_text(_VALID_ROW)
    df = parse_telemetry.load_and_validate(csv_in)

    out_csv = tmp_path / "out.csv"
    out_json = tmp_path / "out.json"
    parse_telemetry.write_normalized(df, out_csv, out_json)

    df2 = pd.read_csv(out_csv)
    pd.testing.assert_frame_equal(df, df2, check_dtype=False)

    data = json.loads(out_json.read_text())
    assert data == df.to_dict(orient="records")


def test_invalid_field(tmp_path: Path) -> None:
    csv_in = tmp_path / "bad.csv"
    # negative voltage violates schema
    csv_in.write_text(_VALID_ROW.replace("0.8", "-0.1"))
    with pytest.raises(ValueError, match="vdd"):
        parse_telemetry.load_and_validate(csv_in)
