from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock

from app.services.supplier_verification_agent import select_verification_batch, verify_supplier_record


def _response(url: str, text: str, status: int = 200) -> Mock:
    response = Mock()
    response.url = url
    response.status_code = status
    response.text = text
    return response


def test_two_independent_sources_corroborate_identity_without_publication_promotion(monkeypatch) -> None:
    monkeypatch.setattr("app.services.supplier_verification_agent._safe_public_url", lambda _: True)
    session = Mock()
    session.get.side_effect = [
        _response("https://alpha.example/", "Alpha Mobility serves Las Vegas and Henderson"),
        _response("https://directory.example/alpha", "Alpha Mobility Las Vegas Nevada"),
    ]
    record = {
        "brand_name": "Alpha Mobility",
        "branch": {"website": "https://alpha.example/"},
        "evidence_refs": ["https://directory.example/alpha"],
        "licenses": [],
    }
    result = verify_supplier_record(record, session=session)
    assert result["stage"] == "IDENTITY_AND_MARKET_CORROBORATED"
    assert result["corroborated_identity"] is True
    assert result["publication_unchanged"] is True
    assert result["case_readiness_unchanged"] is True


def test_official_credential_requires_identifier_and_active_term(monkeypatch) -> None:
    monkeypatch.setattr("app.services.supplier_verification_agent._safe_public_url", lambda _: True)
    session = Mock()
    session.get.return_value = _response(
        "https://data.cms.gov/provider/alpha",
        "Alpha Hospice Las Vegas provider 291999 active certified",
    )
    record = {
        "brand_name": "Alpha Hospice",
        "branch": {"website": None},
        "evidence_refs": ["https://data.cms.gov/provider/alpha"],
        "licenses": [{"authority": "CMS", "identifier": "291999"}],
    }
    result = verify_supplier_record(record, session=session)
    assert result["stage"] == "OFFICIAL_CREDENTIAL_OBSERVED"
    assert result["official_credential_observed"] is True


def test_failed_source_stays_unknown_not_negative(monkeypatch) -> None:
    monkeypatch.setattr("app.services.supplier_verification_agent._safe_public_url", lambda _: True)
    session = Mock()
    session.get.side_effect = __import__("requests").Timeout("slow")
    record = {
        "brand_name": "Unknown Supplier",
        "branch": {"website": "https://unknown.example/"},
        "evidence_refs": [],
        "licenses": [],
    }
    result = verify_supplier_record(record, session=session)
    assert result["stage"] == "NO_MATCH_OBSERVED"
    assert result["publication_unchanged"] is True


def test_batch_prioritizes_never_checked_outcome_critical_candidates() -> None:
    records = [
        {"brand_name": "B", "involvement": "DIRECTORY", "publication": {"status": "CANDIDATE"}},
        {"brand_name": "A", "involvement": "OUTCOME_CRITICAL", "publication": {"status": "CANDIDATE"}},
        {"brand_name": "Public", "involvement": "OUTCOME_CRITICAL", "publication": {"status": "LIMITED"}},
    ]
    assert select_verification_batch(records, 1)[0]["brand_name"] == "A"


def test_batch_rotates_persisted_checks_and_includes_limited_records() -> None:
    records = [
        {"supplier_id": "already", "brand_name": "A", "involvement": "OUTCOME_CRITICAL", "publication": {"status": "CANDIDATE"}},
        {"supplier_id": "limited", "brand_name": "B", "involvement": "DIRECTORY", "publication": {"status": "LIMITED"}},
    ]
    checked = {"already": datetime(2026, 1, 1, tzinfo=timezone.utc)}
    assert select_verification_batch(records, 1, last_checked_by_supplier=checked)[0]["supplier_id"] == "limited"
