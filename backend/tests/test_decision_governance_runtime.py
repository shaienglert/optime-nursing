from __future__ import annotations

from types import SimpleNamespace

from app.services import decision_governance_runtime as runtime


class _Query:
    def __init__(self, rows):
        self.rows = list(rows)

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.rows)

    def first(self):
        return self.rows[0] if self.rows else None


class _DB:
    def __init__(self, knowledge=None, outcomes=None):
        self.knowledge = list(knowledge or [])
        self.outcomes = list(outcomes or [])
        self.added = []
        self.committed = False
        self.closed = False

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "KnowledgeObject":
            return _Query(self.knowledge)
        if name == "ResidentOutcome":
            return _Query(self.outcomes)
        return _Query([])

    def add(self, row):
        self.added.append(row)

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        self.closed = True


def _knowledge(**overrides):
    base = dict(
        id=1,
        object_key="ko-1",
        title="Verified transition evidence",
        category="TRANSITION",
        topic="transition_support",
        entity_type="GENERAL",
        entity_key="ALL",
        property_name="fact",
        fact_value="verified fact",
        source_name="Peer-reviewed journal",
        source_type="ACADEMIC",
        source_reference="doi:test",
        evidence_key="ev-1",
        evidence_summary="summary",
        trust_level="LEVEL_B",
        confidence=0.9,
        verification_status="VERIFIED",
        freshness_status="FRESH",
        conflict_status="NO_CONFLICT",
        evidence_strength="STRONG",
        version="v1",
        status="ACTIVE",
        recommendation_eligible=1,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_knowledge_gate_excludes_unverified_stale_conflicting_objects():
    db = _DB(
        knowledge=[
            _knowledge(id=1, object_key="good"),
            _knowledge(id=2, object_key="unverified", verification_status="UNVERIFIED"),
            _knowledge(id=3, object_key="stale", freshness_status="STALE"),
            _knowledge(id=4, object_key="conflict", conflict_status="OPEN_CONFLICT"),
            _knowledge(id=5, object_key="not-eligible", recommendation_eligible=0),
        ]
    )
    rows = runtime._eligible_knowledge_objects(db)
    assert [row.object_key for row in rows] == ["good"]
    payload = runtime._knowledge_payload(rows)
    assert payload["eligible_count"] == 1
    assert payload["automatic_rank_effect"] == "NONE"


def test_outcomes_are_observational_only_and_never_auto_weight():
    db = _DB(
        outcomes=[
            SimpleNamespace(successful_adjustment=1, loneliness_event=0, relocated_within_24m=0),
            SimpleNamespace(successful_adjustment=0, loneliness_event=1, relocated_within_24m=1),
        ]
    )
    payload = runtime._outcome_payload(db)
    assert payload["sample_size"] == 2
    assert payload["successful_adjustment_rate"] == 0.5
    assert payload["automatic_rank_effect"] == "NONE"
    assert payload["status"] == "OBSERVATIONAL_NOT_CAUSAL"


def test_audit_persistence_writes_agent_delivery_trace_per_recommendation(monkeypatch):
    db = _DB()
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        runtime,
        "_usage_decisions",
        lambda core, row, context: {
            "resident_needs": {
                "decision": "USED",
                "verification": "VERIFIED",
                "confidence": 1.0,
                "reason": "resident needs used",
            }
        },
    )
    core = {
        "decision_intelligence": {"version": "decision-intelligence-runtime-v3.1"},
        "patient_needs_profile": {"needs": [{"parameter_id": "adl_support"}]},
        "recommendation_audit_trace": {
            "facts_used": {"patient_needs": ["adl"], "human_signals": {}},
            "decision_rules_applied": ["unknown_is_not_mismatch"],
            "evidence_references": ["Nevada HCQC / ALiS"],
        },
        "results": [
            {
                "canonical_facility_id": "NV-1",
                "eligibility_status": "ELIGIBLE",
                "care_setting_fit": {"status": "PRIMARY_FIT"},
                "patient_match_score": 60,
                "success_factor_trace": {},
            },
            {
                "canonical_facility_id": "NV-2",
                "eligibility_status": "ELIGIBLE",
                "care_setting_fit": {"status": "PRIMARY_FIT"},
                "patient_match_score": 60,
                "success_factor_trace": {},
            },
        ],
    }
    context = {"knowledge_fabric": {"objects": [_knowledge()]}, "outcome_learning": {"sample_size": 0}}
    result = runtime.persist_recommendation_verification_audits(
        core=core,
        questionnaire_state={"resident_key": "test-resident"},
        governance_context=context,
    )
    assert result["status"] == "PERSISTED"
    assert result["records_written"] == 2
    assert result["agent_usage_records_written"] == 2
    assert result["agent_trace_summary"]["resident_needs"]["used"] == 2
    assert len(db.added) == 4
    assert db.committed is True


def test_every_agent_has_explicit_delivery_decision(monkeypatch):
    monkeypatch.setattr(
        runtime,
        "_regulatory_delivery",
        lambda row: {
            "applicable": True,
            "verified": [],
            "unknown": list(runtime._REGULATORY_PARAMETERS),
            "identity_source": "Nevada HCQC / ALiS",
        },
    )
    core = {
        "patient_needs_profile": {
            "needs": [
                {"parameter_id": "adl_support"},
                {"parameter_id": "pt"},
                {"parameter_id": "activities"},
            ]
        },
        "decision_intelligence": {"agent_evidence_bridge": {"status": "MATERIAL_EVIDENCE_AVAILABLE"}},
    }
    row = {
        "canonical_facility_id": "NV-LIC-4000-AGC-31",
        "client_intent_fit": {
            "nice_match": ["RICH_CULTURE_AND_ACTIVITIES"],
            "nice_unknown": [],
            "public_reputation": {"identity_verified": True, "rating": 2.8, "review_count": 30},
        },
        "agent_person_fit_evidence": [
            {"agent_key": "provider_intelligence", "confidence": 0.82},
            {"agent_key": "activities_intelligence", "confidence": 0.82},
        ],
    }
    context = {"knowledge_fabric": {"eligible_count": 0}, "outcome_learning": {"sample_size": 0}}
    decisions = runtime._usage_decisions(core, row, context)
    assert set(decisions) == set(runtime._ACTIVE_MARKET_AGENTS) | {runtime._REGULATORY_AGENT}
    assert all(item["decision"] in {"USED", "NOT_APPLICABLE"} for item in decisions.values())
    assert decisions["regulatory_intelligence"]["decision"] == "USED"
    assert decisions["regulatory_intelligence"]["verification"] == "UNKNOWN_PRESERVED"
    assert decisions["outcome_learning"]["decision"] == "NOT_APPLICABLE"


def test_attach_surfaces_connection_status_without_changing_rank(monkeypatch):
    monkeypatch.setattr(
        runtime,
        "load_governed_decision_context",
        lambda: {
            "status": "CONNECTED",
            "knowledge_fabric": {"eligible_count": 3, "objects": [], "automatic_rank_effect": "NONE"},
            "outcome_learning": {"sample_size": 4, "automatic_rank_effect": "NONE"},
        },
    )
    monkeypatch.setattr(
        runtime,
        "persist_recommendation_verification_audits",
        lambda **kwargs: {
            "status": "PERSISTED",
            "records_written": 1,
            "agent_usage_records_written": 12,
            "agent_trace_summary": {"resident_needs": {"traces": 1, "used": 1, "not_applicable": 0}},
            "run_id": "r1",
        },
    )
    core = {
        "decision_intelligence": {"version": "decision-intelligence-runtime-v3.1"},
        "recommendation_audit_trace": {},
        "results": [{"canonical_facility_id": "NV-1", "rank_position": 1}],
    }
    out = runtime.attach_governed_knowledge_learning_and_audit(core=core, questionnaire_state={})
    assert out["results"][0]["rank_position"] == 1
    governed = out["decision_intelligence"]["governed_knowledge_learning"]
    assert governed["knowledge_fabric"]["automatic_rank_effect"] == "NONE"
    assert governed["outcome_learning"]["automatic_rank_effect"] == "NONE"
    assert out["recommendation_audit_trace"]["persistence"]["status"] == "PERSISTED"
    assert out["recommendation_audit_trace"]["agent_delivery"]["usage_records_written"] == 12
