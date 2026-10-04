import base64
import gzip
import json
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location('catalog_contract', Path(__file__).resolve().parents[2] / 'scripts/validate_synthetic_pilot_contract.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def dataset(tmp_path, name, rows):
    data = {'record_count': len(rows), 'records': rows}
    (tmp_path / f'{name}.json.gz.b64').write_text(base64.b64encode(gzip.compress(json.dumps(data).encode())).decode())


def pilot(tmp_path):
    dataset(tmp_path, 'facility_universe', [{'canonical_id': 'a', 'facility_name': 'A'}])
    dataset(tmp_path, 'room_inventory', [{'canonical_facility_id': 'a', 'monthly_price_cents': 800000, 'available_units': 1}])
    dataset(tmp_path, 'provider_capabilities', [])
    dataset(tmp_path, 'facility_parameter_evidence', [])


def test_orphan_reference_is_rejected(tmp_path):
    pilot(tmp_path)
    dataset(tmp_path, 'provider_capabilities', [{'canonical_facility_id': 'missing', 'capability': 'x', 'value': 'YES'}])
    assert any('orphan' in error for error in module.validate(tmp_path)['errors'])


def test_same_source_and_scope_contradiction_is_rejected(tmp_path):
    pilot(tmp_path)
    rows = [{'canonical_facility_id': 'a', 'capability': 'x', 'source': 'S', 'value': value} for value in ['YES', 'NO']]
    dataset(tmp_path, 'provider_capabilities', rows)
    assert any('contradictory' in error for error in module.validate(tmp_path)['errors'])


def test_different_capabilities_do_not_imply_clinical_equivalence(tmp_path):
    pilot(tmp_path)
    dataset(tmp_path, 'provider_capabilities', [
        {'canonical_facility_id': 'a', 'capability': 'memory_care', 'value': 'YES'},
        {'canonical_facility_id': 'a', 'capability': 'secured_units', 'value': 'NO'}])
    assert module.validate(tmp_path)['errors'] == []


def test_price_must_use_integral_positive_cents(tmp_path):
    pilot(tmp_path)
    dataset(tmp_path, 'room_inventory', [{'canonical_facility_id': 'a', 'monthly_price_cents': True, 'available_units': -1}])
    assert len(module.validate(tmp_path)['errors']) == 2
