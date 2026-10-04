"""Validate structural pilot truth without inventing clinical equivalences.

Memory care != secured unit, monthly rent != entrance fee and rehabilitation
support != all neurological services. Such combinations require review, not
automatic rewriting or rejection.
"""
import base64
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path


def validate(directory):
    datasets = {path.name.split('.')[0]: json.loads(gzip.decompress(base64.b64decode(path.read_text())))
                for path in Path(directory).glob('*.json.gz.b64')}
    errors = []
    for name, dataset in datasets.items():
        if dataset.get('record_count') != len(dataset['records']):
            errors.append(f'{name}: record_count mismatch')
    facilities = datasets['facility_universe']['records']
    ids = [row['canonical_id'] for row in facilities]
    for identity, count in Counter(ids).items():
        if count != 1:
            errors.append(f'duplicate facility ID: {identity}')
    for name, count in Counter(row['facility_name'].strip().casefold() for row in facilities).items():
        if count != 1:
            errors.append(f'duplicate facility name: {name}')
    for name, dataset in datasets.items():
        if name == 'facility_universe':
            continue
        for row in dataset['records']:
            if row.get('canonical_facility_id') not in ids:
                errors.append(f'{name}: orphan facility reference')
    for row in datasets['room_inventory']['records']:
        price, units = row.get('monthly_price_cents'), row.get('available_units')
        if type(price) is not int or price <= 0:
            errors.append(f"{row['canonical_facility_id']}: invalid monthly_price_cents")
        if type(units) is not int or units < 0:
            errors.append(f"{row['canonical_facility_id']}: invalid available_units")
    for name, field in [('provider_capabilities', 'capability'), ('facility_parameter_evidence', 'parameter_id')]:
        claims = defaultdict(set)
        for row in datasets[name]['records']:
            key = (row['canonical_facility_id'], row[field], row.get('scope'), row.get('scope_name'), row.get('source'))
            claims[key].add(json.dumps(row.get('value'), sort_keys=True))
        for key, values in claims.items():
            if len(values) > 1:
                errors.append(f'{name}: contradictory same-source/scope claim {key}')
    return {'facility_count': len(facilities), 'errors': errors,
            'rule': 'STRUCTURAL_VALIDATION_ONLY; NO_ASSUMED_CLINICAL_EQUIVALENCE'}


if __name__ == '__main__':
    result = validate(Path(__file__).resolve().parents[1] / 'database/synthetic_pilot')
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result['errors']))
