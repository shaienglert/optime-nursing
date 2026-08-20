from __future__ import annotations

import csv
import json
from pathlib import Path


RAW = Path('data/nevada/raw/hcqc_personal_care_agencies.csv')
VERIFIED = Path('data/nevada/verified/personal_care_agency_operational_evidence.json')
LIVE_PROMOTIONS = Path('data/nevada/verified/pca_operational_live_promotions.json')
LIVE_ALLOWLIST = Path('data/nevada/verified/pca_live_operational_allowlist.json')
OUT_JSON = Path('data/nevada/canonical/nevada_las_vegas_valley_personal_care_agencies.json')
OUT_CSV = Path('data/nevada/canonical/nevada_las_vegas_valley_personal_care_agencies.csv')

REGULATORY_FIELDS = [
    'agency_id','agency_name','license_number','license_status','expiration_date',
    'disciplinary_action','address','city','state','zip','county','phone',
    'first_issue_date','administrator','administrator_role','detail_url',
]
OPERATIONAL_FIELDS = [
    'official_website','current_provider_phone','bathing_assistance','dressing_assistance','transfer_assistance',
    'medication_reminders','meal_preparation','light_housekeeping','post_surgical_care',
    'minimum_visit_minutes','minimum_billable_hours','minimum_hours_policy','hourly_rate','employment_model',
    'liability_insurance_verified','bonded_verified','workers_comp_verified','background_check_verified',
    'fixed_caregiver_possible','backup_caregiver_available','supervision_frequency','languages','availability_status',
    'in_facility_care_available','va_community_care_provider_verified','typical_placement_speed',
    'evidence_summary','operational_evidence_status',
]


def _allowlist() -> set[str]:
    if not LIVE_ALLOWLIST.is_file():
        return set()
    payload = json.loads(LIVE_ALLOWLIST.read_text(encoding='utf-8'))
    return {str(value).strip() for value in payload.get('license_numbers') or [] if str(value).strip()}


def _verified_by_license() -> dict[str, dict]:
    allowed = _allowlist()
    verified: dict[str, dict] = {}
    for source in (VERIFIED, LIVE_PROMOTIONS):
        if not source.is_file():
            continue
        payload = json.loads(source.read_text(encoding='utf-8'))
        for row in payload.get('records') or []:
            license_number = str(row.get('license_number') or '').strip()
            if row.get('identity_verified') is True and license_number and license_number in allowed:
                verified[license_number] = row
    return verified


def build() -> dict:
    rows = list(csv.DictReader(RAW.open(encoding='utf-8')))
    valley = [row for row in rows if row.get('is_las_vegas_valley') == 'True']
    verified = _verified_by_license()
    records = []
    for row in valley:
        item = {key: row.get(key, '') for key in REGULATORY_FIELDS}
        item['source_authority'] = 'Nevada HCQC / ALiS'
        item['credential_type'] = 'AGENCY TO PROVIDE PERSONAL CARE SERVICES IN THE HOME'
        item['care_delivery_role'] = 'EXTERNAL_PERSONAL_CARE_AGENCY'
        for key in OPERATIONAL_FIELDS:
            item[key] = [] if key == 'languages' else 'UNKNOWN'
        item['operational_evidence_status'] = 'LICENSE_VERIFIED_OPERATIONAL_UNKNOWN'

        evidence = verified.get(str(row.get('license_number') or '').strip())
        if evidence:
            item['official_website'] = evidence.get('primary_source_url') or 'UNKNOWN'
            for key in OPERATIONAL_FIELDS:
                if key in {'official_website', 'operational_evidence_status'}:
                    continue
                if key in evidence:
                    item[key] = evidence[key]
            item['operational_evidence_status'] = 'PRIMARY_SOURCE_OPERATIONAL_VERIFIED'
        records.append(item)

    records.sort(key=lambda row: (row['city'], row['agency_name'], row['license_number']))
    ids = [row['agency_id'] for row in records]
    assert len(records) == len(set(ids)), 'agency_id must be unique'
    verified_count = sum(row['operational_evidence_status'] == 'PRIMARY_SOURCE_OPERATIONAL_VERIFIED' for row in records)
    assert verified_count == len(verified), (verified_count, len(verified))

    payload = {
        'schema_version': 'optime-nevada-pca-registry-v1.2.0',
        'source_authority': 'Nevada HCQC / ALiS',
        'credential_type': 'AGENCY TO PROVIDE PERSONAL CARE SERVICES IN THE HOME',
        'record_count': len(records),
        'operationally_verified_count': verified_count,
        'operationally_unknown_count': len(records) - verified_count,
        'cities': {
            'LAS VEGAS': sum(row['city'] == 'LAS VEGAS' for row in records),
            'HENDERSON': sum(row['city'] == 'HENDERSON' for row in records),
            'NORTH LAS VEGAS': sum(row['city'] == 'NORTH LAS VEGAS' for row in records),
        },
        'policy': {
            'license_truth': 'HCQC/ALiS is authoritative for license identity and status.',
            'operational_truth': 'Only identity-verified primary provider evidence that is also on the live HCQC allowlist may populate operational fields; all other operational facts remain UNKNOWN.',
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
    print(json.dumps({
        'record_count': payload['record_count'],
        'operationally_verified_count': payload['operationally_verified_count'],
        'operationally_unknown_count': payload['operationally_unknown_count'],
        'cities': payload['cities'],
    }, indent=2))
