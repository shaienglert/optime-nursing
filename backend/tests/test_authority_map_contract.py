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
