from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def test_production_fast_bridge_cannot_queue_research_from_family_search():
    text=(ROOT/"backend/app/services/decision_agent_bridge_fast.py").read_text()
    fn=text.split("def attach_agent_evidence_and_queue_gaps_fast",1)[1]
    assert "AgentQueueItem(" not in fn
    assert "_kick_worker_async()" not in fn

def test_authority_map_forbids_ai_ranking_and_frontend_decision_authority():
    text=(ROOT/"docs/architecture/AUTHORITY_MAP.md").read_text()
    assert "Candidate-ranking AI may not reorder deterministic results." in text
    assert "Frontend may not independently re-rank or re-decide eligibility." in text


def test_semantic_requirement_layer_cannot_queue_or_crawl_from_family_search():
    text=(ROOT/"backend/app/services/semantic_facility_requirements.py").read_text()
    fn=text.split("def apply_semantic_facility_requirements",1)[1]
    assert "_queue_requirement(" not in fn
    assert "_kick_worker_async()" not in fn


def test_a_family_search_makes_no_network_call_and_starts_no_research_thread(monkeypatch):
    """Owner finding 2026-10-02: 73 lookups of pilot.example.invalid during a search came
    from a research crawler the search started. A decision run is deterministic and
    offline; acquisition is a separate, scheduled stage."""
    import json, socket, threading
    monkeypatch.setenv("OPTIME_CANONICAL_MARKET", "synthetic-pilot")
    monkeypatch.setenv("OOMNIK_PILOT_FACILITY_LIMIT", "200")
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_ENABLED", "0")
    lookups=[]
    def blocked(host,*a,**k):
        lookups.append(host); raise OSError("network is not part of a decision")
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    started=[]
    original_start=threading.Thread.start
    def spy(self):
        started.append(self.name); return original_start(self)
    monkeypatch.setattr(threading.Thread, "start", spy)
    from app.services.facility_parameter_service import refresh_runtime_cache
    from app.services.patient_decision_engine import run_patient_decision_engine
    refresh_runtime_cache("offline-search")
    personas=json.loads((ROOT/"backend/gold_examples/oomnik_golden_personas_v1.submissions.json").read_text())["personas"]
    for persona in personas:
        run_patient_decision_engine(persona["questionnaire_state"], "", limit=20)
    assert lookups == []
    assert not [name for name in started if "evidence-worker" in name]
