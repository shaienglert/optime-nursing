from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_live_frontend_libs_do_not_import_legacy_engine():
    allowed={"optime-v2-engine.ts"}
    violations=[]
    for path in (ROOT/"frontend/src/lib").glob("*.ts"):
        if path.name in allowed: continue
        text=path.read_text(encoding="utf-8")
        if '@/lib/optime-v2-engine' in text:
            violations.append(path.name)
    assert violations==[], "Legacy engine dependency remains in frontend libs: "+", ".join(violations)
