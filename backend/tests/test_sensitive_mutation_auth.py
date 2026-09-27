from pathlib import Path


def test_sensitive_system_and_learning_mutations_require_admin_token():
    text = Path("backend/app/main.py").read_text(encoding="utf-8")
    signatures = [
        "decision_engine_process_deferred_reports",
        "run_intelligence",
        "refresh_agent_knowledge_reports",
        "supervisor_run_cycle",
        "provider_identity_reverification_run",
        "create_human_intelligence",
        "create_adaptive_response",
        "create_resident_outcome",
    ]
    for name in signatures:
        start = text.index(f"def {name}") if f"def {name}" in text else text.index(f"async def {name}")
        header = text[start:text.index("):", start) + 2]
        assert "Depends(require_admin_token)" in header, name
