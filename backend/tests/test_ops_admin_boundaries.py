from fastapi.testclient import TestClient

from app.main import app


def test_operational_mutations_and_reports_require_admin(monkeypatch):
    monkeypatch.setenv("OPTIME_ADMIN_TOKEN", "test-ops-admin-token")
    client = TestClient(app)
    routes = (
        ("post", "/decision-engine/deferred-report/process"),
        ("post", "/intelligence/run"),
        ("post", "/expert-agents/knowledge-reports/refresh"),
        ("post", "/supervisor/run-cycle"),
        ("post", "/provider/identity/reverification/run"),
        ("get", "/executive-report/latest"),
        ("get", "/executive-report/latest/full"),
        ("get", "/executive-report/by-id/sample"),
        ("get", "/executive-report/history"),
        ("get", "/executive-report/compare"),
    )
    for method, path in routes:
        response = getattr(client, method)(path)
        assert response.status_code == 401, (method, path, response.status_code)
