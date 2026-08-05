from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.services.facility_snapshot_simulation import ActiveFacilitySnapshotStore


def _row(parameter_id: str, value: str, *, last_verified: str) -> dict:
    return {
        "parameter_id": parameter_id,
        "raw_value": value,
        "status_value": value,
        "source": "CMS prepared snapshot",
        "last_verified": last_verified,
        "evidence_confidence": "HIGH",
    }


def _table(canonical_id: str, *, pt: str, nursing: str, last_verified: str) -> dict:
    return {
        "canonical_facility_id": canonical_id,
        "facility_name": f"Facility {canonical_id}",
        "rows": [
            _row("pt", pt, last_verified=last_verified),
            _row("nursing_24_7", nursing, last_verified=last_verified),
            _row("speech_therapy", "UNKNOWN", last_verified=last_verified),
        ],
    }


def test_snapshot_only_recommendation_and_incremental_refresh() -> None:
    now = datetime.now(timezone.utc)
    fresh = now.isoformat()
    stale = (now - timedelta(days=400)).isoformat()
    store = ActiveFacilitySnapshotStore(
        active_snapshot_version="runtime-v1",
        last_successful_refresh=fresh,
        facility_tables=[
            _table("A", pt="YES", nursing="YES", last_verified=fresh),
            _table("B", pt="UNKNOWN", nursing="YES", last_verified=fresh),
            _table("C", pt="NO", nursing="YES", last_verified=stale),
        ],
        stale_after_days=180,
    )
    needs = [
        {
            "parameter_id": "pt",
            "requirement_level": "REQUIRED",
            "desired_value": "YES",
            "acceptable_values": ["YES"],
        },
        {
            "parameter_id": "nursing_24_7",
            "requirement_level": "HIGH",
            "desired_value": "YES",
            "acceptable_values": ["YES"],
        },
    ]

    unaffected_identity = store.facility_object_identity("A")
    previous_version = store.active_snapshot_version
    with (
        patch(
            "app.services.facility_snapshot_simulation.get_facility_parameter_table",
            side_effect=AssertionError("recommendation must not hydrate facility snapshots"),
        ),
        patch("app.services.external_discovery.run_external_discovery") as external_discovery,
        patch("app.services.runtime_sync_service._rebuild_runtime_artifacts") as runtime_rebuild,
        patch("app.services.facility_parameter_service._build_runtime_payload") as profile_rebuild,
    ):
        before = store.recommend(needs=needs)
        update = store.apply_source_update(
            canonical_facility_id="B",
            parameter_updates={
                "pt": {
                    "raw_value": "YES",
                    "status_value": "YES",
                    "source": "Simulated prepared source release",
                    "evidence_confidence": "HIGH",
                }
            },
            refreshed_at=fresh,
            source_update_id="source-release-2",
        )
        after = store.recommend(needs=needs)
        external_discovery.assert_not_called()
        runtime_rebuild.assert_not_called()
        profile_rebuild.assert_not_called()

    before_by_id = {item["canonical_facility_id"]: item for item in before["results"]}
    after_by_id = {item["canonical_facility_id"]: item for item in after["results"]}
    diagnostics = store.diagnostics()

    assert before["snapshot_only"] is True
    assert before["internet_crawl_performed"] is False
    assert before["facility_profiles_rebuilt"] is False
    assert previous_version != store.active_snapshot_version
    assert update["affected_facilities"] == ["B"]
    assert update["changed_parameters"] == ["pt"]
    assert update["unchanged_facilities_reused"] == ["A", "C"]
    assert store.facility_object_identity("A") == unaffected_identity
    assert diagnostics["facility_refresh_counts"] == {"A": 0, "B": 1, "C": 0}
    assert diagnostics["parameter_refresh_counts"]["B"] == {"pt": 1}
    assert diagnostics["network_request_count"] == 0
    assert diagnostics["profile_rebuild_count"] == 0
    assert before_by_id["B"]["match_score"] != after_by_id["B"]["match_score"]
    assert before_by_id["B"]["eligibility_status"] == "INSUFFICIENT_EVIDENCE"
    assert after_by_id["B"]["eligibility_status"] == "ELIGIBLE"
    assert after_by_id["B"]["changed_parameters_since_previous_snapshot"] == ["pt"]
    assert after_by_id["B"]["unchanged_parameters_reused"] == 2
    assert "speech_therapy" in after_by_id["B"]["missing_parameters"]
    assert "pt" in after_by_id["C"]["stale_parameters"]
    assert before["recommendation_response_time_ms"] < 250
    assert after["recommendation_response_time_ms"] < 250