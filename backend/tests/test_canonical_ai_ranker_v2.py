from __future__ import annotations

import pytest

from app.services.canonical_ai_ranker_v2 import rank_all_canonical_must_eligible_v2


def _row(index: int) -> dict:
    return {
        "canonical_facility_id": f"F{index}",
        "facility_name": f"Facility {index}",
        "city": "Las Vegas",
        "state": "NV",
        "canonical_type": "ASSISTED_LIVING_RFG",
        "canonical_evidence_state": True,
        "authoritative_must": {
            "status": "PASS",
            "pass": ["req:med"],
            "pending_verification": [],
            "fail": [],
            "authoritative": True,
        },
        "parameters": {
            "medication_support": {"raw_value": "YES", "source": "official", "last_verified": "2026-08-26"},
            "social_engagement": {"raw_value": "YES" if index % 2 else "UNKNOWN", "source": "official" if index % 2 else "Not verified"},
        },
        "semantic_service_levels": {
            "MEDICATION_SUPPORT": {"level": "MANAGEMENT_OR_SUPERVISION", "confidence": "HIGH", "source": "OFFICIAL_PROVIDER_WEBSITE"}
        },
    }


def _client():
    return {
        "canonical_facts": [{"fact_key": "age", "value": 90}],
        "requirements": [
            {"requirement_id": "req:med", "importance": "MUST", "capability_key": "MEDICATION_SUPPORT"},
            {"requirement_id": "req:social", "importance": "NICE", "capability_key": "SOCIAL_ENGAGEMENT"},
        ],
        "strategy_candidates": [{"strategy_id": "ASSISTED_LIVING", "status": "LEADING"}],
        "statement_accounting": [],
        "governance": {"single_interpretation": True},
    }


def test_every_must_eligible_candidate_is_ai_scored_and_leaders_are_ai_adjudicated(monkeypatch):
    monkeypatch.setenv("OPTIME_V2_AI_RANKING_BATCH_SIZE", "10")
    seen_score_ids = []

    def transport(prompt):
        role = prompt["role"]
        if role == "OPTIME_NURSING_CANONICAL_AI_SCORER_V2":
            ids = [row["canonical_facility_id"] for row in prompt["facilities"]]
            seen_score_ids.extend(ids)
            return {
                "scored_candidates": [
                    {
                        "canonical_facility_id": cid,
                        "score": 90 - int(cid[1:]),
                        "reason": "governed fit",
                        "unresolved_requirement_ids": ["req:social"],
                        "information_deficits": ["social preference evidence incomplete"],
                    }
                    for cid in ids
                ]
            }
        if role == "OPTIME_NURSING_CANONICAL_AI_FINAL_ADJUDICATOR_V2":
            ids = [row["canonical_facility_id"] for row in prompt["leading_candidates"]]
            return {"ordered_candidate_ids": list(reversed(ids)), "reasons_by_id": {cid: "final AI order" for cid in ids}}
        raise AssertionError(role)

    rows = [_row(i) for i in range(1, 16)]
    ranked = rank_all_canonical_must_eligible_v2(rows, _client(), transport=transport)
    assert set(seen_score_ids) == {f"F{i}" for i in range(1, 16)}
    assert len(seen_score_ids) == 15
    assert len(ranked) == 15
    assert all((row["ai_ranking"] or {}).get("status") in {"AI_GLOBAL_RANKED", "AI_BATCH_SCORED"} for row in ranked)
    assert all((row["ai_ranking"] or {}).get("all_must_eligible_ai_scored") is True for row in ranked)


def test_ai_cannot_mark_passed_must_requirement_as_unresolved():
    def transport(prompt):
        if prompt["role"] == "OPTIME_NURSING_CANONICAL_AI_SCORER_V2":
            cid = prompt["facilities"][0]["canonical_facility_id"]
            return {"scored_candidates": [{"canonical_facility_id": cid, "score": 80, "reason": "bad contradiction", "unresolved_requirement_ids": ["req:med"], "information_deficits": []}]}
        raise AssertionError("adjudication should not be reached")

    with pytest.raises(RuntimeError, match="CONTRADICTS_MUST_PASS"):
        rank_all_canonical_must_eligible_v2([_row(1)], _client(), transport=transport)


def test_ranker_rejects_non_pass_candidate_before_ai_call():
    row = _row(1)
    row["authoritative_must"]["status"] = "PENDING_VERIFICATION"
    with pytest.raises(RuntimeError, match="NON_PASS"):
        rank_all_canonical_must_eligible_v2([row], _client(), transport=lambda _: {})
