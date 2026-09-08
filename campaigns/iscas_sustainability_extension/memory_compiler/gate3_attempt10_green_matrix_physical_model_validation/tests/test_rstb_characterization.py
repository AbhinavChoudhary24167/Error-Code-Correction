import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('rstb_characterize', ROOT/'scripts/rstb_characterize.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_interpolation_and_domain_guard():
    table = {'input_slew_ns':[.01,.11], 'load_pf':[.1,.3], 'values_ns':[[1,3],[2,4]]}
    assert module.interpolate(table,.06,.2) == pytest.approx(2.5)
    with pytest.raises(ValueError, match='extrapolation forbidden'):
        module.interpolate(table,0,.2)
    with pytest.raises(ValueError, match='extrapolation forbidden'):
        module.interpolate(table,.05,.4)

def test_frozen_units_capacitance_and_threshold_conversion():
    cells, macros, factor = module.load_models()
    assert factor == pytest.approx(4/3)
    assert macros[module.MACROS[0]]['rise_capacitance'] == .448008
    assert macros[module.MACROS[1]]['rise_capacitance'] == .250926
    assert all(x['max_transition'] == .351 for x in macros.values())
    assert all(x['available_strengths'][-1] == 16 for x in cells.values())

def test_table_diagnostics_reproduce_independent_opensta():
    payload = json.loads((ROOT/'rstb/RSTB_INTERFACE_CHARACTERIZATION.json').read_text())
    assert len(payload['table_opensta_crosscheck']) == 8
    assert max(x['absolute_error_ns'] for x in payload['table_opensta_crosscheck']) < 1e-6
    assert len(payload['actual_diagnostics']['zero_wire']) == 24
    assert len(payload['actual_diagnostics']['local_placement']) == 6
    assert len(payload['actual_diagnostics']['post_route']) == 3
    assert payload['classification_letter'] == 'D'
    assert payload['rstb_constraint_changed'] is False

def test_postroute_slew_frozen_and_parasitics_not_pin_cap():
    payload = json.loads((ROOT/'rstb/RSTB_INTERFACE_CHARACTERIZATION.json').read_text())
    expected = {'u_data/rstb': .619147718, 'u_protected_memory.u_data/rstb':.615635812,
                'u_protected_memory.u_ecc/rstb':.307288498}
    for row in payload['actual_diagnostics']['post_route']:
        assert max(row['pins'][row['target']].values()) == expected[row['target']]
        assert row['pin_cap_in_spef'] is False
        assert row['spef_d_net_parasitic_capacitance_pf'] < .003
        assert row['reset_path']['upstream_terminal'] == 'rstb'

def test_spice_connectivity_is_not_characterization():
    payload = json.loads((ROOT/'rstb/RSTB_INTERFACE_CHARACTERIZATION.json').read_text())
    for row in payload['spice_connectivity'].values():
        assert row['primitive_gate_connection_count'] > 0
        assert row['capacitance_recharacterization'] == 'NOT_QUALIFIED'
        assert row['transient_simulation'] == 'NOT_RUN'
