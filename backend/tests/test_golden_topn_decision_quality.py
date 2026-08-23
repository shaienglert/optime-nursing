from __future__ import annotations

import os
from unittest.mock import patch

from app.services.facility_parameter_service import refresh_runtime_cache
from app.services.patient_decision_engine import run_patient_decision_engine


def _run_ready(questionnaire: dict, query: str, limit: int = 5) -> dict:
    ai_result = {"decision_readiness": "READY", "next_question": None, "statements": []}
    with patch.dict(
        os.environ,
        {
            "OPTIME_CANONICAL_MARKET": "las-vegas",
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_SEMANTIC_AI_REQUIRED": "1",
        },
        clear=False,
    ), patch(
        "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai",
        return_value=ai_result,
    ):
        refresh_runtime_cache("golden_topn_case")
        return run_patient_decision_engine(questionnaire, query, limit=limit)


def _modalities(row: dict) -> set[str]:
    values = {str(row.get("canonical_type") or "UNKNOWN").upper()}
    values.update(str(value or "UNKNOWN").upper() for value in row.get("housing_modalities") or [])
    return values


def test_golden_independent_client_top5_is_led_by_independent_products():
    result = _run_ready(
        {
            "relationship": "My mother",
            "ageGroup": "80-84",
            "assistanceLevel": "Fully independent",
            "memoryStatus": "No",
            "budget": 8000,
            "locationCity": "Las Vegas",
        },
        (
            "My mother is 82 and is looking for senior living in Las Vegas. "
            "She is fully independent with bathing, dressing, toileting, transfers and medications. "
            "She has no memory concerns, no mobility limitation, and no medical or nursing needs. "
            "Her monthly budget is $8,000."
        ),
    )
    rows = result.get("results") or []
    assert len(rows) == 5, result
    assert all((row.get("client_intent_fit") or {}).get("hard_gate") != "FAIL" for row in rows)
    independent = [row for row in rows if _modalities(row) & {"INDEPENDENT_LIVING", "LIFE_PLAN_CCRC"}]
    assert len(independent) >= 3, [(row.get("facility_name"), sorted(_modalities(row))) for row in rows]
    assert _modalities(rows[0]) & {"INDEPENDENT_LIVING", "LIFE_PLAN_CCRC"}, rows[0]
    small_rfg = [
        row for row in rows
        if row.get("canonical_type") == "ASSISTED_LIVING_RFG"
        and not (_modalities(row) & {"INDEPENDENT_LIVING", "LIFE_PLAN_CCRC"})
    ]
    assert len(small_rfg) <= 1, [row.get("facility_name") for row in rows]


def test_golden_ongoing_adl_client_top5_is_assisted_living_primary_fit():
    result = _run_ready(
        {
            "relationship": "Dad",
            "ageGroup": "80-84",
            "assistanceLevel": "Needs assistance with bathing and dressing",
            "memoryStatus": "No",
            "budget": 6500,
            "locationCity": "Las Vegas",
        },
        (
            "My father is 84 and lives in Las Vegas. He needs ongoing daily help with bathing, dressing and medications. "
            "He is mentally alert, has no dementia, remains mobile, and is not expected to recover to full independence. "
            "His monthly budget is $6,500."
        ),
    )
    rows = result.get("results") or []
    assert len(rows) == 5, result
    assert all(row.get("canonical_type") == "ASSISTED_LIVING_RFG" for row in rows), [
        (row.get("facility_name"), row.get("canonical_type")) for row in rows
    ]
    assert all((row.get("care_setting_fit") or {}).get("status") == "PRIMARY_FIT" for row in rows)
    assert all((row.get("client_intent_fit") or {}).get("hard_gate") != "FAIL" for row in rows)


def test_golden_memory_care_client_top5_requires_confirmed_memory_fit():
    result = _run_ready(
        {
            "relationship": "My mother",
            "ageGroup": "80-84",
            "assistanceLevel": "Needs supervision and daily assistance",
            "memoryStatus": "Dementia",
            "budget": 9000,
            "locationCity": "Las Vegas",
        },
        (
            "My mother is 82, has diagnosed dementia with wandering risk, and needs memory-care supervision and daily assistance. "
            "We need an appropriate memory care setting in Las Vegas. Her monthly budget is $9,000."
        ),
    )
    rows = result.get("results") or []
    assert rows, result
    assert all((row.get("client_intent_fit") or {}).get("hard_gate") != "FAIL" for row in rows)
    assert all((row.get("care_setting_fit") or {}).get("status") == "PRIMARY_FIT" for row in rows), [
        (row.get("facility_name"), row.get("care_setting_fit"), row.get("memory_care_classification")) for row in rows
    ]
    assert all(str(row.get("memory_care_classification") or "").upper() == "CONFIRMED" for row in rows), [
        (row.get("facility_name"), row.get("memory_care_classification")) for row in rows
    ]


def test_golden_skilled_nursing_client_does_not_surface_residential_only_settings():
    result = _run_ready(
        {
            "relationship": "Dad",
            "ageGroup": "80-84",
            "assistanceLevel": "Requires 24/7 nursing care",
            "memoryStatus": "No",
            "budget": 12000,
            "locationCity": "Las Vegas",
        },
        (
            "My father requires 24/7 skilled nursing and ongoing clinical monitoring in Las Vegas. "
            "This is not only help with bathing or dressing; he requires a skilled nursing facility. "
            "His monthly budget is $12,000."
        ),
    )
    rows = result.get("results") or []
    assert rows, result
    assert all(row.get("canonical_type") == "SKILLED_NURSING" for row in rows), [
        (row.get("facility_name"), row.get("canonical_type"), row.get("care_setting_fit")) for row in rows
    ]
    assert all((row.get("care_setting_fit") or {}).get("status") == "PRIMARY_FIT" for row in rows)
    assert all((row.get("client_intent_fit") or {}).get("hard_gate") != "FAIL" for row in rows)
