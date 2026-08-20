from __future__ import annotations

import csv
import json
from pathlib import Path


RAW = Path('data/nevada/raw/hcqc_personal_care_agencies.csv')
OUT_JSON = Path('data/nevada/canonical/nevada_las_vegas_valley_personal_care_agencies.json')
OUT_CSV = Path('data/nevada/canonical/nevada_las_vegas_valley_personal_care_agencies.csv')

REGULATORY_FIELDS = [
    'agency_id','agency_name','license_number','license_status','expiration_date',
    'disciplinary_action','address','city','state','zip','county','phone',
    'first_issue_date','administrator','administrator_role','detail_url',
]
OPERATIONAL_FIELDS = [
    'official_website','bathing_assistance','dressing_assistance','transfer_assistance',
    'medication_reminders','meal_preparation','light_housekeeping',
    'minimum_visit_minutes','minimum_billable_hours','hourly_rate','employment_model',
    'liability_insurance_verified','workers_comp_verified','background_check_verified',
    'fixed_caregiver_possible','languages','availability_status','operational_evidence_status',
]


def build() -> dict:
    rows = list(csv.DictReader(RAW.open(encoding='utf-8')))
    valley = [row for row in rows if row.get('is_las_vegas_valley') == 'True']
    records = []
    for row in valley:
        item = {key: row.get(key, '') for key in REGULATORY_FIELDS}
        item['source_authority'] = 'Nevada HCQC / ALiS'
        item['credential_type'] = 'AGENCY TO PROVIDE PERSONAL CARE SERVICES IN THE HOME'
        item['care_delivery_role'] = 'EXTERNAL_PERSONAL_CARE_AGENCY'
        for key in OPERATIONAL_FIELDS:
            item[key] = [] if key == 'languages' else 'UNKNOWN'
        item['operational_evidence_status'] = 'LICENSE_VERIFIED_OPERATIONAL_UNKNOWN'
        records.append(item)

    records.sort(key=lambda row: (row['city'], row['agency_name'], row['license_number']))
    ids = [row['agency_id'] for row in records]
    assert len(records) == len(set(ids)), 'agency_id must be unique'

    payload = {
        'schema_version': 'optime-nevada-pca-registry-v1.0.0',
        'source_authority': 'Nevada HCQC / ALiS',
        'credential_type': 'AGENCY TO PROVIDE PERSONAL CARE SERVICES IN THE HOME',
        'record_count': len(records),
        'cities': {
            'LAS VEGAS': sum(row['city'] == 'LAS VEGAS' for row in records),
            'HENDERSON': sum(row['city'] == 'HENDERSON' for row in records),
            'NORTH LAS VEGAS': sum(row['city'] == 'NORTH LAS VEGAS' for row in records),
        },
        'policy': {
            'license_truth': 'HCQC/ALiS is authoritative for license identity and status.',
            'operational_truth': 'Operational and commercial facts remain UNKNOWN until primary-source or direct-contact verification.',
            'bundle_rule': 'A PCA may be bundled with an Independent Living community only when outside-care permission or a facility-agency relationship is verified.',
        },
        'records': records,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    fields = [*REGULATORY_FIELDS, 'source_authority','credential_type','care_delivery_role', *OPERATIONAL_FIELDS]
    with OUT_CSV.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    return payload


if __name__ == '__main__':
    payload = build()
    print(json.dumps({'record_count': payload['record_count'], 'cities': payload['cities']}, indent=2))
