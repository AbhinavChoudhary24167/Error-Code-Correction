import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(relative):
    return json.loads((ROOT/relative).read_text(encoding='utf-8'))

def test_physical_matrix_has_original_and_corrected_provenance_rows():
    data=load('green_matrix/GREEN_MATRIX_PHYSICAL.json')
    assert data['row_count']==20
    assert {r['liberty_model'] for r in data['rows']}=={'UPSTREAM_ORIGINAL','RESEARCH_CORRECTED_DIAGNOSTIC'}
    assert len([r for r in data['rows'] if r['liberty_model']=='RESEARCH_CORRECTED_DIAGNOSTIC' and r['architecture_id']=='U0' and r['area_total_um2']=='NOT_MEASURED'])==5
    assert len([r for r in data['rows'] if r['liberty_model']=='RESEARCH_CORRECTED_DIAGNOSTIC' and r['architecture_id']=='E0' and isinstance(r['area_total_um2'],(int,float))])==5
    assert all(r['gate3_status'].startswith('FAIL') for r in data['rows'])

def test_schema_requires_every_stable_physical_column():
    schema=load('green_matrix/GREEN_MATRIX_SCHEMA.json')
    item=schema['properties']['rows']['items']
    assert item['additionalProperties'] is False
    for required in ('architecture_id','liberty_model','energy_access_j','total_lifecycle_carbon_kgCO2e','qualification_status','source_provenance'):
        assert required in item['required']
        assert required in item['properties']
    assert {'type': 'integer'} in item['properties']['seed']['oneOf']

def test_carbon_never_promotes_unqualified_energy_or_sky130_proxy():
    data=load('carbon/CARBON_RESULTS.json')
    assert data['status']=='NOT_QUALIFIED'
    assert data['rows']
    assert all(r['carbon_qualification']=='NOT_QUALIFIED' for r in data['rows'])
    assert all(r['total_lifecycle_carbon_kgCO2e']=='NOT_QUALIFIED' for r in data['rows'])
    assumptions=load('carbon/CARBON_ASSUMPTIONS.json')
    assert assumptions['technology']['exact_node_in_carbon_calib'] is False
    assert assumptions['computation_gate']['nearest_node_fallback_for_campaign'] is False

def test_normalization_and_pareto_are_evidence_gated():
    metadata=load('green_matrix/GREEN_MATRIX_METADATA.json')
    assert metadata['normalization']['status']=='BLOCKED_NO_FULLY_QUALIFIED_ROWS'
    assert metadata['raw_matrix']['eligible_row_count']==0
    pareto=load('pareto/PARETO_RESULTS.json')
    assert pareto['status']=='BLOCKED_NO_FULLY_QUALIFIED_ROWS'
    assert pareto['eligible_row_count']==0
    assert pareto['frontier_row_ids']==[]
    assert pareto['hypervolume']=='NOT_COMPUTED_NO_QUALIFIED_NORMALIZED_FRONT'

def test_csv_physical_header_keeps_required_fields():
    with (ROOT/'green_matrix/GREEN_MATRIX_PHYSICAL.csv').open(newline='',encoding='utf-8') as stream:
        rows=list(csv.DictReader(stream))
    assert len(rows)==20
    assert {'architecture_id','liberty_model','gate3_status','power_qualification','energy_qualification'} <= set(rows[0])
