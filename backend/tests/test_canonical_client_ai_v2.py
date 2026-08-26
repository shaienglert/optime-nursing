from __future__ import annotations

import pytest

from app.services.canonical_client_ai_v2 import build_canonical_client_ai_state


def _packet():
    return {
        "statement_accounting": [
            {
                "statement_id": "s1",
                "raw_text": "My mother is 90 and needs help with bathing, dressing and medications.",
                "semantic_meaning": "Resident needs ADL and medication support.",
                "importance": "MUST",
                "knowledge_state": "KNOWN",
                "owner": "CLIENT",
                "used_in_requirement_ids": ["req:adl", "req:med"],
                "used_in_strategy_ids": ["ASSISTED_LIVING"],
            },
            {
                "statement_id": "s2",
                "raw_text": "Her husband died two months ago and she does not want to be alone.",
                "semantic_meaning": "Recent bereavement and high social-transition need; spouse is deceased, not a current co-resident.",
                "importance": "CONTEXT",
                "knowledge_state": "KNOWN",
                "owner": "CLIENT",
                "used_in_requirement_ids": ["req:social"],
                "used_in_strategy_ids": ["ASSISTED_LIVING"],
            },
        ],
        "canonical_facts": [
            {"fact_key": "resident_age", "value": 90, "knowledge_state": "KNOWN", "source_statement_ids": ["s1"]},
            {"fact_key": "current_household", "value": "SINGLE", "knowledge_state": "KNOWN", "source_statement_ids": ["s2"]},
        ],
        "requirements": [
            {"requirement_id": "req:adl", "importance": "MUST", "capability_key": "ADL_SUPPORT", "required_service_level": "BATHING_AND_DRESSING_ASSISTANCE", "client_expression": "help with bathing and dressing", "knowledge_state": "KNOWN", "owner": "CLIENT", "source_statement_ids": ["s1"]},
            {"requirement_id": "req:med", "importance": "MUST", "capability_key": "MEDICATION_SUPPORT", "required_service_level": "MANAGEMENT_OR_ADMINISTRATION", "client_expression": "help with medications", "knowledge_state": "KNOWN", "owner": "CLIENT", "source_statement_ids": ["s1"]},
            {"requirement_id": "req:social", "importance": "NICE", "capability_key": "SOCIAL_ENGAGEMENT", "required_service_level": "HIGH", "client_expression": "does not want to be alone", "knowledge_state": "KNOWN", "owner": "CLIENT", "source_statement_ids": ["s2"]},
        ],
        "strategy_candidates": [
            {"strategy_id": "ASSISTED_LIVING", "status": "LEADING", "rank_hint": 1, "rationale": "Persistent ADL and medication support with social transition needs.", "required_capability_keys": ["ADL_SUPPORT", "MEDICATION_SUPPORT"], "source_statement_ids": ["s1", "s2"]}
        ],
        "next_question": {"question": None, "resolves_statement_ids": [], "reason": None},
        "research_requests": [],
        "decision_readiness": "READY",
    }


def test_one_ai_contract_owns_client_requirements_and_strategy():
    state = build_canonical_client_ai_state({}, "ignored", transport=lambda _: _packet())
    assert state["decision_readiness"] == "READY"
    assert {r["capability_key"] for r in state["requirements"]} == {"ADL_SUPPORT", "MEDICATION_SUPPORT", "SOCIAL_ENGAGEMENT"}
    assert state["strategy_candidates"][0]["strategy_id"] == "ASSISTED_LIVING"
    assert state["governance"]["downstream_raw_text_reparse_forbidden"] is True


def test_bereavement_does_not_require_current_couple_strategy():
    state = build_canonical_client_ai_state({}, "ignored", transport=lambda _: _packet())
    household = next(f for f in state["canonical_facts"] if f["fact_key"] == "current_household")
    assert household["value"] == "SINGLE"
    assert all("COUPLE" not in str(s["strategy_id"]) for s in state["strategy_candidates"])


def test_requirement_without_statement_provenance_fails_closed():
    packet = _packet()
    packet["requirements"][0]["source_statement_ids"] = ["missing"]
    with pytest.raises(RuntimeError, match="UNGROUNDED_REQUIREMENT"):
        build_canonical_client_ai_state({}, "ignored", transport=lambda _: packet)


def test_ready_cannot_coexist_with_client_question():
    packet = _packet()
    packet["next_question"] = {"question": "What matters more?", "resolves_statement_ids": ["s1"], "reason": "conflict"}
    with pytest.raises(RuntimeError, match="READY_WITH_QUESTION"):
        build_canonical_client_ai_state({}, "ignored", transport=lambda _: packet)


def test_material_client_conflict_requires_one_grounded_question():
    packet = _packet()
    packet["statement_accounting"][0]["knowledge_state"] = "CONFLICT"
    packet["decision_readiness"] = "NEEDS_CLARIFICATION"
    packet["next_question"] = {"question": "Do you need staff to manage the medications or only remind her?", "resolves_statement_ids": ["s1"], "reason": "Medication service level changes MUST eligibility."}
    state = build_canonical_client_ai_state({}, "ignored", transport=lambda _: packet)
    assert state["decision_readiness"] == "NEEDS_CLARIFICATION"
    assert state["next_question"]["resolves_statement_ids"] == ["s1"]
