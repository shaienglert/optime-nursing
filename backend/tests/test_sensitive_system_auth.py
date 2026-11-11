from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from app import main


ROUTES = [
    ('POST', '/human-intelligence'),
    ('POST', '/human-intelligence/adaptive-response'),
    ('POST', '/resident-outcomes'),
    ('POST', '/recommendation/knowledge-guard'),
    ('GET', '/supervisor/overview'),
    ('GET', '/supervisor/incidents'),
    ('GET', '/supervisor/stale-usage'),
    ('GET', '/diagnostics/medication-evidence-audit'),
    ('GET', '/diagnostics/must-gate-screen'),
    ('GET', '/intelligence/facilities/1'),
]


@pytest.mark.parametrize('method,path', ROUTES)
@pytest.mark.parametrize('credential', [None, 'wrong', 'unconfigured'])
def test_sensitive_routes_deny_before_accessing_database(monkeypatch, method, path, credential):
    monkeypatch.setenv('OPTIME_ADMIN_TOKEN', 'system-test-token')
    if credential == 'unconfigured':
        monkeypatch.delenv('OPTIME_ADMIN_TOKEN')
        credential = 'system-test-token'
    database = Mock(side_effect=AssertionError('unauthorized database access'))
    previous = main.app.dependency_overrides.copy()
    main.app.dependency_overrides[main.get_db] = database
    try:
        headers = {'X-Admin-Token': credential} if credential else {}
        response = TestClient(main.app).request(method, path, headers=headers, json={})
        assert response.status_code == 401
        database.assert_not_called()
    finally:
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(previous)


def test_authorized_admin_reaches_supervisor(monkeypatch):
    monkeypatch.setenv('OPTIME_ADMIN_TOKEN', 'system-test-token')
    database = object()
    service = Mock(return_value={'safe': True})
    monkeypatch.setattr(main, 'stale_usage_summary', service)
    previous = main.app.dependency_overrides.copy()
    main.app.dependency_overrides[main.get_db] = lambda: database
    try:
        response = TestClient(main.app).get('/supervisor/stale-usage', headers={'X-Admin-Token': 'system-test-token'})
        assert response.status_code == 200
        assert response.json() == {'safe': True}
        service.assert_called_once_with(database, hours=24)
    finally:
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(previous)
