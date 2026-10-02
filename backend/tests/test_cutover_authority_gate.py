from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_raw_narrative_mapper_is_not_called_by_decision_core():
    text=(ROOT/"backend/app/services/decision_engine_core.py").read_text(encoding="utf-8")
    assert 'RAW_NARRATIVE_NOT_DECISION_INPUT' in text
    pipeline=(ROOT/'backend/app/services/decision_pipeline.py').read_text(encoding='utf-8')
    assert 'materialize_questionnaire(decision_profile)' in pipeline
    assert 'natural_language_query=""' in pipeline

def test_frontend_and_candidate_ai_are_not_decision_authorities():
    authority=(ROOT/"docs/architecture/AUTHORITY_MAP.md").read_text(encoding="utf-8")
    assert "Candidate-ranking AI may not reorder deterministic results." in authority
    assert "Frontend may not independently re-rank or re-decide eligibility." in authority
