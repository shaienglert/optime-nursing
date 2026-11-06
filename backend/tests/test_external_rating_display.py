from copy import deepcopy
from datetime import date
from unittest.mock import Mock

import pytest
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services import external_rating_display as display
from app.services.client_intent_runtime import evaluate_candidate_intent, intent_rank_key
from app.services.external_rating_api import external_rating_router
from app.services.must_ai_nice_pipeline import _layered_rank
from app.services.regulatory_quality_layer import measure_values


def facility():
    return {"canonical_facility_id": "nv-test", "facility_name": "Example Community",
            "address": "123 Main Road", "city": "Las Vegas", "canonical_type": "ASSISTED_LIVING_RFG",
            "care_setting_fit": {"status": "PRIMARY_FIT"}}


def record():
    return {**facility(), "identity_verified": True, "google": {"place_id": "ChIJ_test"},
            "us_news": {"recognition": "Best Assisted Living", "assessment_year": date.today().year,
                        "observed_at": date.today().isoformat(), "display_permission_verified": True,
                        "source_url": "https://health.usnews.com/best-senior-living/example-123"}}


@pytest.fixture
def sources(monkeypatch):
    source = record()
    monkeypatch.setattr(display, "_records", lambda: [source])
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    return source


def test_no_google_key_does_not_fetch_or_relabel_generic_ratings(sources, monkeypatch):
    get = Mock(side_effect=AssertionError("No configured key: no network"))
    monkeypatch.setattr(display.requests, "get", get)
    row = {**facility(), "public_reputation": {"rating": 4.9, "source": "PUBLIC_LOCAL_BUSINESS_INDEX"}}
    result = display.external_ratings_for_facility(row)
    assert result["google"]["rating"] is None
    assert result["us_news"]["recognition"] == "Best Assisted Living"
    assert result["us_news"]["rating"] is None
    assert result["ranking_eligible"] is False
    get.assert_not_called()


@pytest.mark.parametrize("change", [{"synthetic_pilot": True}, {"address": "999 Other Street"}, {"city": "Reno"}, {"canonical_facility_id": "another"}])
def test_no_reviews_for_wrong_or_synthetic_identity(sources, change):
    result = display.external_ratings_for_facility({**facility(), **change})
    assert result["google"]["status"] == result["us_news"]["status"] == "UNAVAILABLE"


def test_google_fetch_uses_api_identity_and_server_secret_only(sources, monkeypatch):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "test-only-key")
    payload = {"displayName": {"text": "Example Community"},
               "formattedAddress": "123 Main Rd, Las Vegas, NV, USA", "rating": 4.7,
               "userRatingCount": 82, "googleMapsUri": "https://maps.google.com/?cid=123"}
    response = Mock()
    response.json.return_value = payload
    get = Mock(return_value=response)
    monkeypatch.setattr(display.requests, "get", get)
    result = display.external_ratings_for_facility(facility())
    assert result["google"]["rating"] == 4.7
    assert result["google"]["review_count"] == 82
    assert result["google"]["ranking_eligible"] is False
    assert "test-only-key" not in str(result)
    assert get.call_args.kwargs["headers"]["X-Goog-Api-Key"] == "test-only-key"
    assert get.call_args.kwargs["timeout"] == 6
    payload["displayName"]["text"] = "A different community"
    assert display.external_ratings_for_facility(facility())["google"]["rating"] is None


def test_google_failure_does_not_remove_us_news_or_return_a_zero(sources, monkeypatch):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "test-only-key")
    monkeypatch.setattr(display.requests, "get", Mock(side_effect=requests.Timeout("test-only-key")))
    result = display.external_ratings_for_facility(facility())
    assert result["google"]["status"] == "SOURCE_UNAVAILABLE"
    assert result["google"]["rating"] is None
    assert result["us_news"]["status"] == "AVAILABLE"
    assert "test-only-key" not in str(result)


@pytest.mark.parametrize("field,value", [
    ("display_permission_verified", False), ("assessment_year", True),
    ("assessment_year", 2999), ("source_url", "https://health.usnews.com.evil.test/x"),
    ("source_url", "javascript:alert(1)"), ("observed_at", "bad-date"),
])
def test_us_news_needs_exact_provenance_and_permission(sources, field, value):
    sources["us_news"][field] = value
    assert display.external_ratings_for_facility(facility())["us_news"]["status"] == "UNAVAILABLE"


def test_ambiguous_registry_fails_closed(sources, monkeypatch):
    monkeypatch.setattr(display, "_records", lambda: [sources, deepcopy(sources)])
    assert display.external_ratings_for_facility(facility())["us_news"]["recognition"] is None


def test_external_ratings_cannot_change_fit_evidence_count_or_legacy_key():
    intent = {"must_haves": [], "nice_to_haves": []}
    baseline = facility()
    fit = evaluate_candidate_intent(baseline, intent)
    changed = {**baseline, "public_reputation": {"rating": 5, "review_count": 100000, "identity_verified": True},
               "external_ratings": {"google": {"rating": 5}, "us_news": {"recognition": "Best"}},
               "agent_person_fit_evidence": [{"payload": {"public_rating": 5, "public_review_count": 100000}}]}
    changed_fit = evaluate_candidate_intent(changed, intent)
    assert changed_fit == fit
    a, b = {**baseline, "client_intent_fit": fit}, {**changed, "client_intent_fit": deepcopy(fit)}
    b["client_intent_fit"]["public_reputation"] = changed["public_reputation"]
    assert intent_rank_key(a) == intent_rank_key(b)
    assert "public_rating" not in measure_values(b)
    assert "public_review_count" not in measure_values(b)


def test_top_ten_order_and_true_ties_ignore_external_scores_and_presence():
    rows = []
    for i in range(20):
        row = {**facility(), "canonical_facility_id": str(i), "budget_exception": i > 15,
               "client_intent_fit": {"hard_gate": "PASS", "nice_match": ["GARDEN"] if i < 6 else [],
                                     "relevant_evidence_known_count": 0}}
        rows.append(row)
    before = _layered_rank(deepcopy(rows))
    for i, row in enumerate(rows):
        row["client_intent_fit"]["public_reputation"] = {"source": "GOOGLE", "rating": 5 - i / 20,
                                                        "review_count": 10000 - i, "identity_verified": True}
        if i % 2:
            row["external_ratings"] = {"google": {"rating": 1}, "us_news": {"recognition": "Best", "assessment_year": 2026}}
    after = _layered_rank(rows)
    assert [r["canonical_facility_id"] for r in before[:10]] == [r["canonical_facility_id"] for r in after[:10]]
    assert [r["rank_group_signature"] for r in before] == [r["rank_group_signature"] for r in after]


def test_public_display_endpoint_has_no_store_and_no_secret(sources):
    app = FastAPI()
    app.include_router(external_rating_router(lambda: {"nv-test": facility()}))
    client = TestClient(app)
    response = client.get("/canonical-facilities/nv-test/external-ratings")
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert response.json()["us_news"]["assessment_year"] == date.today().year
    assert "place_id" not in response.text and "display_permission" not in response.text
    assert client.get("/canonical-facilities/no-such-facility/external-ratings").status_code == 404
