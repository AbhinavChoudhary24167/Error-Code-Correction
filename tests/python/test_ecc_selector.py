from ecc_selector import select_ecc


def test_select_ecc_taec_choice():
    ecc = select_ecc(
        ber=1e-6,
        burst_length=2,
        vdd=0.6,
        energy_budget=2e-15,
        sustainability_mode=False,
        required_correction=1,
    )
    assert ecc is not None
    assert ecc.ecc_type == "TAEC"
    assert ecc.code == "(75,64)-I6"
