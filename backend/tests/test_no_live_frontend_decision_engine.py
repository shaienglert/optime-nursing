from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
LIVE_ROOTS=[ROOT/"frontend/src/app",ROOT/"frontend/src/components"]
FORBIDDEN=("@/lib/optime-v2-engine","runOptimeV2Engine")

def test_live_frontend_cannot_import_or_run_legacy_decision_engine():
    violations=[]
    for base in LIVE_ROOTS:
        for path in base.rglob("*"):
            if path.suffix not in {".ts",".tsx",".js",".jsx"}: continue
            text=path.read_text(encoding="utf-8")
            if any(token in text for token in FORBIDDEN):
                violations.append(str(path.relative_to(ROOT)))
    assert violations==[], "Legacy frontend decision authority found in live UI: "+", ".join(violations)

def test_authority_map_declares_backend_decision_engine_only():
    text=(ROOT/"docs/architecture/AUTHORITY_MAP.md").read_text(encoding="utf-8")
    assert "Frontend may not independently re-rank or re-decide eligibility." in text
