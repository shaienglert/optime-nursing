from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, List

import pytest

from app.services.evidence_engine_service import (
    NormalizedEvidenceItem,
    _mark_conflicts_and_preferred,
    _merge_duplicates,
    _validation_report,
)


def _sample_item(
    *,
    evidence_id: str,
    facility_id: int | None,
    parameter_id: str,
    parameter_value: str | None,
    source: str,
    source_type: str,
    verification_status: str,
    confidence_score: float,
    dedup_group_key: str,
    verified_at: datetime | None = None,
) -> NormalizedEvidenceItem:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return NormalizedEvidenceItem(
        evidence_id=evidence_id,
        facility_id=facility_id,
        parameter_id=parameter_id,
        parameter_name=parameter_id,
        parameter_value=parameter_value,
        source=source,
        source_type=source_type,
        source_url="",
        collection_method="test",
        collected_at=now,
        verified_at=verified_at or now,
        verification_status=verification_status,
        confidence_score=confidence_score,
        importance_score=50.0,
        expires_at=None,
        runtime_version="test-runtime",
        connector="TEST",
        affects_recommendation=True,
        dedup_group_key=dedup_group_key,
        raw_payload={},
    )


def test_merge_duplicates_collapses_to_single_record_with_provenance() -> None:
    first = _sample_item(
        evidence_id="a1",
        facility_id=1,
        parameter_id="pt",
        parameter_value="YES",
        source="Facility portal",
        source_type="FACILITY_PORTAL",
        verification_status="PARTIALLY_VERIFIED",
        confidence_score=0.72,
        dedup_group_key="group-1",
    )
    second = _sample_item(
        evidence_id="a2",
        facility_id=1,
        parameter_id="pt",
        parameter_value="YES",
        source="CMS Provider Staffing",
        source_type="CMS",
        verification_status="VERIFIED",
        confidence_score=0.95,
        dedup_group_key="group-1",
    )

    merged = _merge_duplicates([first, second])

    assert len(merged) == 1
    row = merged[0]
    assert row.source_type == "CMS"
    assert row.verification_status == "VERIFIED"
    assert sorted(row.raw_payload["merged_from"]) == ["a1", "a2"]
    assert len(row.raw_payload["source_history"]) == 2


def test_conflict_resolution_prefers_verified_high_confidence_source() -> None:
    cms_row = _sample_item(
        evidence_id="cms-1",
        facility_id=5,
        parameter_id="memory_care",
        parameter_value="YES",
        source="CMS",
        source_type="CMS",
        verification_status="VERIFIED",
        confidence_score=0.94,
        dedup_group_key="x1",
    )
    portal_row = _sample_item(
        evidence_id="portal-1",
        facility_id=5,
        parameter_id="memory_care",
        parameter_value="NO",
        source="Facility portal",
        source_type="FACILITY_PORTAL",
        verification_status="PARTIALLY_VERIFIED",
        confidence_score=0.80,
        dedup_group_key="x2",
    )

    resolution = _mark_conflicts_and_preferred([cms_row, portal_row])

    assert resolution["cms-1"]["conflict_status"] == "CONFLICT"
    assert resolution["portal-1"]["conflict_status"] == "CONFLICT"
    assert resolution["cms-1"]["preferred"] is True
    assert resolution["portal-1"]["preferred"] is False


class _QueryStub:
    def __init__(self, rows: List[Any]) -> None:
        self._rows = rows

    def filter(self, *_args: Any, **_kwargs: Any) -> "_QueryStub":
        return self

    def all(self) -> List[Any]:
        return self._rows


class _DbStub:
    def __init__(self, rows: List[Any]) -> None:
        self._rows = rows

    def query(self, *_args: Any, **_kwargs: Any) -> _QueryStub:
        return _QueryStub(self._rows)


@pytest.mark.parametrize(
    "rows,expected",
    [
        (
            [
                SimpleNamespace(
                    evidence_id="e1",
                    facility_id=10,
                    parameter_id="p_required",
                    parameter_value="YES",
                    verification_status="VERIFIED",
                    preferred=True,
                    dedup_group_key="k1",
                ),
                SimpleNamespace(
                    evidence_id="e2",
                    facility_id=10,
                    parameter_id="p_optional",
                    parameter_value="UNKNOWN",
                    verification_status="UNKNOWN",
                    preferred=True,
                    dedup_group_key="k2",
                ),
                SimpleNamespace(
                    evidence_id="e6",
                    facility_id=10,
                    parameter_id="p_missing",
                    parameter_value="NO",
                    verification_status="VERIFIED",
                    preferred=True,
                    dedup_group_key="k6",
                ),
            ],
            {
                "no_duplicate_evidence": True,
                "no_orphan_evidence": True,
                "every_recommendation_parameter_references_evidence": True,
                "unknown_is_preserved": True,
            },
        ),
        (
            [
                SimpleNamespace(
                    evidence_id="e3",
                    facility_id=None,
                    parameter_id="p_required",
                    parameter_value="YES",
                    verification_status="VERIFIED",
                    preferred=True,
                    dedup_group_key="dupe",
                ),
                SimpleNamespace(
                    evidence_id="e4",
                    facility_id=11,
                    parameter_id="p_required",
                    parameter_value="NO",
                    verification_status="VERIFIED",
                    preferred=True,
                    dedup_group_key="dupe",
                ),
                SimpleNamespace(
                    evidence_id="e5",
                    facility_id=11,
                    parameter_id="p_optional",
                    parameter_value="UNKNOWN",
                    verification_status="VERIFIED",
                    preferred=True,
                    dedup_group_key="k3",
                ),
            ],
            {
                "no_duplicate_evidence": False,
                "no_orphan_evidence": False,
                "every_recommendation_parameter_references_evidence": False,
                "unknown_is_preserved": False,
            },
        ),
    ],
)
def test_validation_report_flags_core_integrity_rules(
    monkeypatch: pytest.MonkeyPatch,
    rows: List[Any],
    expected: dict[str, bool],
) -> None:
    monkeypatch.setattr(
        "app.services.evidence_engine_service._parameter_registry_index",
        lambda: {
            "p_required": {"ranking_eligibility": True, "hard_filter_eligibility": False},
            "p_missing": {"ranking_eligibility": False, "hard_filter_eligibility": True},
            "p_optional": {"ranking_eligibility": False, "hard_filter_eligibility": False},
        },
    )

    report = _validation_report(_DbStub(rows))

    assert report["no_duplicate_evidence"] is expected["no_duplicate_evidence"]
    assert report["no_orphan_evidence"] is expected["no_orphan_evidence"]
    assert (
        report["every_recommendation_parameter_references_evidence"]
        is expected["every_recommendation_parameter_references_evidence"]
    )
    assert report["unknown_is_preserved"] is expected["unknown_is_preserved"]
