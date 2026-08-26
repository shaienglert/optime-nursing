from __future__ import annotations

from app.services.canonical_facility_runtime_v2 import merge_canonical_facility_evidence
from app.services.canonical_must_guard_v2 import evaluate_canonical_must_v2


def _candidate():
    return {
        "canonical_id": "NV-A",
        "facility_name": "A",
        "city": "Las Vegas",
        "state": "NV",
        "canonical_type": "ASSISTED_LIVING_RFG",
    }


def _table(med="UNKNOWN", adl="YES"):
    return {
        "canonical_facility_id": "NV-A",
        "facility_name": "A",
        "city": "Las Vegas",
        "state": "NV",
        "canonical_type": "ASSISTED_LIVING_RFG",
        "rows": [
            {"parameter_id": "medication_support", "raw_value": med, "source": "registry" if med != "UNKNOWN" else "Not verified", "conflict_status": "NONE"},
            {"parameter_id": "adl_support", "raw_value": adl, "source": "Nevada HCQC" if adl != "UNKNOWN" else "Not verified", "conflict_status": "NONE"},
        ],
    }


def _agent_med(level="MANAGEMENT_OR_SUPERVISION"):
    return {
        "record_id": 1,
        "source": "OFFICIAL_PROVIDER_WEBSITE",
        "confidence": 0.9,
        "created_at": "2026-08-26T00:00:00Z",
        "payload": {
            "market": "las-vegas",
            "source_url": "https://example.com/care",
            "observed_at": "2026-08-26T00:00:00Z",
            "medication_support_verified": True,
            "evidence_interpretation_mode": "AI_SEMANTIC_GUARDIAN",
            "semantic_evidence_interpretation": {
                "closed_world_validated": True,
                "capabilities": [
                    {"capability": "MEDICATION_SUPPORT", "level": level, "confidence": "HIGH", "evidence_summary": "Staff manages resident medications."},
                ],
            },
        },
    }


def test_agent_semantic_evidence_and_parameter_table_become_one_facility_state():
    state = merge_canonical_facility_evidence(
        candidate=_candidate(),
        parameter_table=_table(),
        agent_records=[_agent_med()],
        known_parameter_ids={"medication_support", "adl_support"},
    )
    assert state["canonical_evidence_state"] is True
    assert state["parameters"]["medication_support"]["raw_value"] == "YES"
    assert state["semantic_service_levels"]["MEDICATION_SUPPORT"]["level"] == "MANAGEMENT_OR_SUPERVISION"


def test_medication_management_must_passes_only_when_required_service_level_is_proven():
    state = merge_canonical_facility_evidence(
        candidate=_candidate(),
        parameter_table=_table(),
        agent_records=[_agent_med("MANAGEMENT_OR_SUPERVISION")],
        known_parameter_ids={"medication_support", "adl_support"},
    )
    result = evaluate_canonical_must_v2(
        state,
        {"requirements": [{
            "requirement_id": "req:med",
            "capability_key": "MEDICATION_SUPPORT",
            "required_service_level": "MANAGEMENT_OR_SUPERVISION",
            "client_expression": "manage her medications",
            "evidence_parameter_ids": ["medication_support"],
            "semantic_evidence_needed": False,
        }]},
    )
    assert result["status"] == "PASS"
    assert result["pass"] == ["req:med"]


def test_reminder_only_does_not_pass_medication_management_and_does_not_become_fail():
    state = merge_canonical_facility_evidence(
        candidate=_candidate(),
        parameter_table=_table(),
        agent_records=[_agent_med("REMINDER_ONLY")],
        known_parameter_ids={"medication_support", "adl_support"},
    )
    result = evaluate_canonical_must_v2(
        state,
        {"requirements": [{
            "requirement_id": "req:med",
            "capability_key": "MEDICATION_SUPPORT",
            "required_service_level": "MANAGEMENT_OR_SUPERVISION",
            "client_expression": "manage her medications",
            "evidence_parameter_ids": ["medication_support"],
            "semantic_evidence_needed": False,
        }]},
    )
    assert result["status"] == "PENDING_VERIFICATION"
    assert result["fail"] == []
    assert result["pending_verification"] == ["req:med"]


def test_research_false_is_not_promoted_to_explicit_no():
    record = _agent_med()
    record["payload"]["medication_support_verified"] = False
    record["payload"]["semantic_evidence_interpretation"]["capabilities"][0]["level"] = "NONE_OR_NOT_STATED"
    state = merge_canonical_facility_evidence(
        candidate=_candidate(),
        parameter_table=_table(),
        agent_records=[record],
        known_parameter_ids={"medication_support", "adl_support"},
    )
    assert state["parameters"]["medication_support"]["raw_value"] == "UNKNOWN"


def test_direct_explicit_no_can_fail_generic_bound_must():
    state = merge_canonical_facility_evidence(
        candidate=_candidate(),
        parameter_table=_table(med="NO"),
        agent_records=[],
        known_parameter_ids={"medication_support", "adl_support"},
    )
    result = evaluate_canonical_must_v2(
        state,
        {"requirements": [{
            "requirement_id": "req:custom",
            "capability_key": "CUSTOM_CAPABILITY",
            "required_service_level": "UNKNOWN",
            "client_expression": "custom",
            "evidence_parameter_ids": ["medication_support"],
            "semantic_evidence_needed": False,
        }]},
    )
    assert result["status"] == "FAIL"
