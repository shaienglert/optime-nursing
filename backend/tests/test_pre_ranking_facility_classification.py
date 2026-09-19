from __future__ import annotations

from unittest.mock import patch

from app.services import _classify_facilities_before_ranking
from app.services.facility_parameter_service import (
    get_facility_knowledge_catalog,
    query_facility_knowledge_catalog,
    refresh_runtime_cache,
)


def test_synthetic_pilot_rehab_is_classified_before_client_readiness() -> None:
    profile = {
        "needs": [
            {"parameter_id": "pt"},
            {"parameter_id": "ot"},
            {"parameter_id": "speech_therapy"},
            {"parameter_id": "post_stroke_neuro_evidence"},
        ]
    }
    with patch.dict(
        "os.environ",
        {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "50"},
        clear=False,
    ):
        refresh_runtime_cache("test_pre_ranking_rehab_classification")
        discovery = _classify_facilities_before_ranking(profile)

    assert discovery["status"] == "COMPLETED_PRE_RANKING"
    assert discovery["total_facilities_classified"] == 50
    assert discovery["classification_counts"]["REHABILITATION"] == 6
    assert discovery["verified_capability_match_count"] > 0
    assert discovery["relevant_candidate_count"] >= discovery["verified_capability_match_count"]
    assert discovery["identities_hidden_pending_client_input"] is True


def test_catalog_stores_provenance_and_retrieves_rehab_from_tables() -> None:
    with patch.dict(
        "os.environ",
        {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "50"},
        clear=False,
    ):
        refresh_runtime_cache("test_catalog_rehab_retrieval")
        catalog = get_facility_knowledge_catalog()
        query = query_facility_knowledge_catalog(
            required_parameter_ids=["pt", "ot", "speech_therapy", "post_stroke_neuro_evidence"]
        )

    assert len(catalog) == 50
    assert query["candidate_count"] > 0
    assert query["candidate_count"] == 8
    assert query["verified_capability_match_count"] == 8
    assert query["classification_counts"] == {"REHABILITATION": 6, "SKILLED_NURSING": 2}
    assert query["excluded_explicit_negative_count"] == 42
    assert query["unknown_is_not_negative"] is True
    rehab = next(row for row in catalog.values() if row["classification"] == "REHABILITATION")
    assert rehab["capabilities"]["pt"]["value"] == "YES"
    assert rehab["capabilities"]["pt"]["source"]
    assert rehab["capabilities"]["pt"]["last_verified"]
    assert rehab["capabilities"]["pt"]["provenance"]["synthetic_pilot"] is True


def test_catalog_does_not_treat_missing_capability_as_negative() -> None:
    with patch.dict(
        "os.environ",
        {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "50"},
        clear=False,
    ):
        refresh_runtime_cache("test_catalog_unknown_is_not_negative")
        query = query_facility_knowledge_catalog(required_parameter_ids=["capability_not_yet_researched"])

    assert query["candidate_count"] == 50
    assert query["verified_capability_match_count"] == 0
    assert query["pending_verification_count"] == 50
    assert query["excluded_explicit_negative_count"] == 0
