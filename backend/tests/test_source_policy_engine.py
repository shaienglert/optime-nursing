from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.source_lifecycle_service import (
    LIFECYCLE_APPROVED,
    LIFECYCLE_BLOCKED_TEMPORARILY,
    LIFECYCLE_DISCOVERED,
    LIFECYCLE_INTEGRATED,
    LIFECYCLE_OWNER_DECISION_REQUIRED,
    LIFECYCLE_REJECTED,
    LIFECYCLE_UNDER_REVIEW,
    ensure_registry_shape,
    evaluate_source_policy_for_record,
    generate_status_snapshot,
    register_source_candidate,
    render_status_report,
    transition_source_status,
)
from app.services.source_policy_engine import (
    POLICY_AUTO_APPROVE,
    POLICY_AUTO_BLOCK,
    POLICY_AUTO_INTEGRATED,
    POLICY_AUTO_REJECT,
    POLICY_NEEDS_MORE_EVIDENCE,
    POLICY_OWNER_REVIEW,
    REASON_AUTHORITY_VERIFIED,
)


SCRIPT_PATH = REPO_ROOT / "scripts" / "migrate_source_policy_registry.py"
SPEC = importlib.util.spec_from_file_location("migrate_source_policy_registry", SCRIPT_PATH)
assert SPEC and SPEC.loader
MIGRATION = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MIGRATION
SPEC.loader.exec_module(MIGRATION)


def source(**overrides: object) -> dict:
    record = {
        "source_id": "SRC-TEST-1",
        "source_name": "CMS Provider Information",
        "market": "florida",
        "state": "FL",
        "authority_level": "Federal government",
        "source_type": "CSV",
        "official_url": "https://data.cms.gov/provider-data/dataset/4pq5-n9py",
        "download_url": "https://data.cms.gov/provider-data/provider.csv",
        "authentication_requirement": "None",
        "discovery_agent": "Provider Intelligence Agent",
        "discovery_date": "2026-08-04T00:00:00Z",
        "last_validation": "2026-08-04T00:00:00Z",
        "lifecycle_status": LIFECYCLE_DISCOVERED,
        "owner": "Data Quality & Trust Agent",
        "priority": "P0",
        "facility_types_covered": ["Skilled Nursing Facility", "Nursing Facility"],
        "markets_affected": ["florida"],
        "dependencies": ["Canonical universe builder"],
        "evidence": ["reports/source.json"],
    }
    record.update(overrides)
    return record


def payload(records: list[dict]) -> dict:
    return ensure_registry_shape({"records": records})


def test_official_government_csv_auto_approved() -> None:
    record = source()
    outcome = evaluate_source_policy_for_record(record)
    assert outcome["policy_status"] == POLICY_AUTO_APPROVE
    assert outcome["proposed_lifecycle_status"] == LIFECYCLE_APPROVED
    assert REASON_AUTHORITY_VERIFIED in outcome["policy_reason_codes"]


def test_successfully_imported_source_auto_integrated() -> None:
    record = source(lifecycle_status=LIFECYCLE_INTEGRATED, last_successful_import="2026-08-04T00:00:00Z", reason="integrated into canonical build")
    outcome = evaluate_source_policy_for_record(record)
    assert outcome["policy_status"] == POLICY_AUTO_INTEGRATED
    assert outcome["proposed_lifecycle_status"] == LIFECYCLE_INTEGRATED


def test_government_portal_with_temporary_outage_auto_blocked() -> None:
    record = source(
        source_name="State Licensing Portal",
        source_type="WEBSITE",
        download_url=None,
        official_url="https://state.gov/licensing",
        authority_level="Nevada state licensing authority",
        blocking_issue="HTTP 403 bot/challenge blocked",
    )
    outcome = evaluate_source_policy_for_record(record)
    assert outcome["policy_status"] == POLICY_AUTO_BLOCK
    assert outcome["proposed_lifecycle_status"] == LIFECYCLE_BLOCKED_TEMPORARILY
    assert outcome["next_review_date"]


def test_robots_endpoint_auto_rejected() -> None:
    record = source(source_name="AHCA robots", source_type="WEBSITE", official_url="https://ahca.myflorida.com/robots.txt")
    outcome = evaluate_source_policy_for_record(record)
    assert outcome["policy_status"] == POLICY_AUTO_REJECT
    assert outcome["proposed_lifecycle_status"] == LIFECYCLE_REJECTED


def test_commercial_directory_rejected_as_authoritative_source() -> None:
    record = source(source_name="Seniorly Directory", authority_level="Commercial", official_url="https://seniorly.com/florida")
    outcome = evaluate_source_policy_for_record(record)
    assert outcome["policy_status"] == POLICY_AUTO_REJECT


def test_unknown_authority_remains_under_review() -> None:
    record = source(authority_level="", source_type="PORTAL_EXPORT", official_url="https://example.com/export", download_url=None)
    outcome = evaluate_source_policy_for_record(record)
    assert outcome["policy_status"] == POLICY_NEEDS_MORE_EVIDENCE
    assert outcome["proposed_lifecycle_status"] == LIFECYCLE_UNDER_REVIEW


def test_legal_uncertainty_escalates_to_owner() -> None:
    record = source(blocking_issue="legal terms unclear for automated use")
    outcome = evaluate_source_policy_for_record(record)
    assert outcome["policy_status"] == POLICY_OWNER_REVIEW
    assert outcome["proposed_lifecycle_status"] == LIFECYCLE_OWNER_DECISION_REQUIRED


def test_paid_source_escalates_to_owner() -> None:
    record = source(authentication_requirement="Paid subscription")
    outcome = evaluate_source_policy_for_record(record)
    assert outcome["policy_status"] == POLICY_OWNER_REVIEW


def test_duplicate_source_candidate_writes_are_idempotent() -> None:
    registry = payload([])
    first = register_source_candidate(registry, source(source_id="SRC-DUP-1"))
    second = register_source_candidate(registry, source(source_id="SRC-DUP-1"))
    assert first["source_id"] == second["source_id"]
    assert registry["record_count"] == 1


def test_integrated_source_cannot_lose_status_without_evidence() -> None:
    record = source(lifecycle_status=LIFECYCLE_INTEGRATED, last_successful_import="2026-08-04T00:00:00Z")
    with pytest.raises(ValueError):
        transition_source_status(record, LIFECYCLE_BLOCKED_TEMPORARILY, reason_codes=[], next_review_date="2026-08-05T00:00:00Z")


def test_blocked_source_requires_next_review_date() -> None:
    record = source()
    with pytest.raises(ValueError):
        transition_source_status(record, LIFECYCLE_BLOCKED_TEMPORARILY, reason_codes=["ACCESS_TEMPORARILY_FAILED"])


def test_invalid_lifecycle_transition_rejected() -> None:
    record = source()
    with pytest.raises(ValueError):
        transition_source_status(record, LIFECYCLE_INTEGRATED, reason_codes=["SUCCESSFUL_IMPORT_EVIDENCE"])


def test_owner_decision_preserved() -> None:
    record = source(lifecycle_status=LIFECYCLE_OWNER_DECISION_REQUIRED, owner_decision="Await commercial approval", owner_decision_date="2026-08-04T00:00:00Z")
    outcome = evaluate_source_policy_for_record(record)
    assert outcome["policy_status"] == POLICY_OWNER_REVIEW
    with pytest.raises(ValueError):
        transition_source_status(record, LIFECYCLE_APPROVED, reason_codes=["AUTHORITY_VERIFIED"])


def test_report_generated_from_registry_only() -> None:
    registry = payload([
        source(source_id="SRC-A", lifecycle_status=LIFECYCLE_INTEGRATED, last_successful_import="2026-08-04T00:00:00Z"),
        source(source_id="SRC-B", source_name="AHCA robots", lifecycle_status=LIFECYCLE_REJECTED, official_url="https://ahca.myflorida.com/robots.txt"),
    ])
    for record in registry["records"]:
        evaluate_source_policy_for_record(record)
    report = render_status_report(registry)
    assert "Total discovered authoritative sources in registry: **2**" in report
    assert "| florida | 2 |" in report


def test_owner_decision_percentage_calculation() -> None:
    registry = payload([
        source(source_id="SRC-1", lifecycle_status=LIFECYCLE_OWNER_DECISION_REQUIRED),
        source(source_id="SRC-2", lifecycle_status=LIFECYCLE_INTEGRATED, last_successful_import="2026-08-04T00:00:00Z", reason="integrated"),
    ])
    for record in registry["records"]:
        evaluate_source_policy_for_record(record)
    snapshot = generate_status_snapshot(registry)
    assert snapshot["owner_decision_count"] >= 1
    assert snapshot["owner_decision_percentage"] >= 50.0


def test_migration_of_current_29_records() -> None:
    original = json.loads((REPO_ROOT / "database" / "source_lifecycle_registry.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_registry = Path(tmp_dir) / "registry.json"
        temp_registry.write_text(json.dumps(original, indent=2), encoding="utf-8")
        migrated = MIGRATION.migrate_payload(json.loads(temp_registry.read_text(encoding="utf-8")))
        assert migrated["payload"]["record_count"] == 29
        assert len(migrated["changes"]) == 29
        assert all(change["policy_after"] for change in migrated["changes"])
        report = MIGRATION.build_migration_report(migrated["payload"], migrated["before_status_distribution"], migrated["changes"])
        assert report["registry_record_count"] == 29
        assert report["owner_decision_percentage"] < 20.0