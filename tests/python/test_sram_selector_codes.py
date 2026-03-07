from ecc_selector import select


def _params():
    return {
        "node": 14,
        "vdd": 0.8,
        "temp": 75.0,
        "capacity_gib": 64 / (1024 * 1024),
        "ci": 0.3,
        "bitcell_um2": 0.08,
        "lifetime_h": 8760.0,
    }


def test_sram_codes_supported_in_selector():
    codes = ["sram-secded-8", "sram-taec-8", "sram-bch-8", "sram-polar-8"]
    result = select(codes, **_params())
    assert result["best"] is not None
    assert len(result["candidate_records"]) == 4
