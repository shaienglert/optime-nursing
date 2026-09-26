from unittest.mock import patch

from app.services.governed_evidence_runtime import agent_and_provider_payloads
from app.services.facility_parameter_service import refresh_runtime_cache


def test_pilot_parameters_are_available_to_must_gate(monkeypatch):
    monkeypatch.setenv('OPTIME_CANONICAL_MARKET', 'synthetic-pilot')
    refresh_runtime_cache('pilot-projection-test')
    from app.services.facility_parameter_service import get_facility_knowledge_catalog
    catalog = get_facility_knowledge_catalog()
    cid = next(cid for cid, row in catalog.items() if row['capabilities']['medication_support']['value'] == 'YES')
    payloads = agent_and_provider_payloads({'canonical_facility_id': cid})
    assert any(p.get('medication_support_verified') is True and p.get('synthetic_pilot') is True for p in payloads)


def test_pilot_row_cannot_authorize_real_market_evidence(monkeypatch):
    monkeypatch.setenv('OPTIME_CANONICAL_MARKET', 'las-vegas')
    assert agent_and_provider_payloads({'canonical_facility_id': 'PILOT-NV-003', 'synthetic_pilot': True}) == []


def test_unverified_parameter_cannot_pass_pilot_gate(monkeypatch):
    monkeypatch.setenv('OPTIME_CANONICAL_MARKET', 'synthetic-pilot')
    with patch('app.services.facility_parameter_service.get_canonical_facility_index', return_value={'PILOT-NV-003': {'synthetic_pilot': True}}), patch('app.services.facility_parameter_service.get_facility_knowledge_catalog', return_value={'PILOT-NV-003': {'capabilities': {'medication_support': {'value': 'YES', 'verification_status': 'NOT_VERIFIED', 'provenance': {'synthetic_pilot': True}}}}}):
        assert not any(p.get('medication_support_verified') for p in agent_and_provider_payloads({'canonical_facility_id': 'PILOT-NV-003'}))


def test_ai_claim_ledger_reads_same_pilot_parameter_facts(monkeypatch):
    monkeypatch.setenv('OPTIME_CANONICAL_MARKET', 'synthetic-pilot')
    refresh_runtime_cache('pilot-claim-ledger-test')
    from app.services.semantic_preference_runtime import build_facility_claim_ledger
    ledger = build_facility_claim_ledger({'canonical_facility_id': 'PILOT-NV-001'})
    claims = {c['path']: c['value'] for c in ledger['claims']}
    assert claims['facility.pilot_parameter_evidence.verified_parameters.activities'] == 'YES'
    assert claims['facility.pilot_parameter_evidence.verified_parameters.adl_support'] == 'NO'
    assert claims['facility.pilot_parameter_evidence.synthetic_pilot'] is True
