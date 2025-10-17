import re

from sram_ecc_benchmark import sustainability_benchmark


def test_sustainability_benchmark_bch_nesii_positive(capsys):
    sustainability_benchmark(16 * 8)
    out = capsys.readouterr().out
    matches = re.findall(r"BCH: ESII=[^,]+, NESII=([0-9.]+)", out)
    assert matches, "Expected BCH entries in sustainability benchmark output"
    for value in matches:
        assert float(value) > 0.0
