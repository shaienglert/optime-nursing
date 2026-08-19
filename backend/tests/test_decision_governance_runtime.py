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


def test_audit_persistence_writes_one_record_per_recommendation(monkeypatch):
    db = _DB()
    monkeypatch.setattr(runtime, "SessionLocal", lambda: db)
    core = {
        "decision_intelligence": {"version": "decision-intelligence-runtime-v2"},
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
    context = {"knowledge_fabric": {"objects": [_knowledge()]}}
    result = runtime.persist_recommendation_verification_audits(
        core=core,
        questionnaire_state={"resident_key": "test-resident"},
        governance_context=context,
    )
    assert result["status"] == "PERSISTED"
    assert result["records_written"] == 2
    assert len(db.added) == 2
    assert db.committed is True


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
        lambda **kwargs: {"status": "PERSISTED", "records_written": 1, "run_id": "r1"},
    )
    core = {
        "decision_intelligence": {"version": "decision-intelligence-runtime-v2"},
        "recommendation_audit_trace": {},
        "results": [{"canonical_facility_id": "NV-1", "rank_position": 1}],
    }
    out = runtime.attach_governed_knowledge_learning_and_audit(core=core, questionnaire_state={})
    assert out["results"][0]["rank_position"] == 1
    governed = out["decision_intelligence"]["governed_knowledge_learning"]
    assert governed["knowledge_fabric"]["automatic_rank_effect"] == "NONE"
    assert governed["outcome_learning"]["automatic_rank_effect"] == "NONE"
    assert out["recommendation_audit_trace"]["persistence"]["status"] == "PERSISTED"
