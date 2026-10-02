from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
LIVE=[ROOT/'frontend'/'src'/'app',ROOT/'frontend'/'src'/'components',ROOT/'frontend'/'src'/'context']

def test_live_frontend_has_no_legacy_decision_authority():
    violations=[]
    for root in LIVE:
        for path in root.rglob('*'):
            if path.suffix not in {'.ts','.tsx','.js','.jsx'}: continue
            text=path.read_text(encoding='utf-8')
            if 'optime-v2-engine' in text or 'runOptimeV2Engine' in text: violations.append(str(path.relative_to(ROOT)))
    assert violations==[], violations

def test_live_pipeline_marks_structured_profile_authoritative_before_core():
    pipeline=(ROOT/'backend'/'app'/'services'/'decision_pipeline.py').read_text(encoding='utf-8')
    assert 'materialize_questionnaire(decision_profile)' in pipeline
    core=(ROOT/'backend'/'app'/'services'/'decision_engine_core.py').read_text(encoding='utf-8')
    assert 'if questionnaire_state.get("_structured_profile_authoritative") is True:' in core
    assert 'RAW_NARRATIVE_NOT_DECISION_INPUT' in core
