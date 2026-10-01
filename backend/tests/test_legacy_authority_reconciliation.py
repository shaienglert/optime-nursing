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

def test_backend_raw_narrative_mapper_is_not_called_by_decision_core():
    text=(ROOT/'backend'/'app'/'services'/'decision_engine_core.py').read_text(encoding='utf-8')
    active=[line for line in text.splitlines() if '_map_natural_language(' in line and not line.lstrip().startswith('def ')]
    assert active==[], active
