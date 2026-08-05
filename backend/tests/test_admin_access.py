from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.admin_access import require_admin_for_refresh, verify_admin_secret


def test_admin_secret_is_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPTIME_ADMIN_SECRET", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        verify_admin_secret(None)
    assert exc_info.value.status_code == 403


def test_admin_secret_rejects_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPTIME_ADMIN_SECRET", "expected-secret")
    with pytest.raises(HTTPException) as exc_info:
        verify_admin_secret("wrong-secret")
    assert exc_info.value.status_code == 403


def test_admin_secret_accepts_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPTIME_ADMIN_SECRET", "expected-secret")
    verify_admin_secret("expected-secret")


def test_read_only_refresh_dependency_needs_no_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPTIME_ADMIN_SECRET", raising=False)
    require_admin_for_refresh(refresh=False, x_optime_admin_secret=None)


def test_refresh_dependency_requires_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPTIME_ADMIN_SECRET", "expected-secret")
    with pytest.raises(HTTPException) as exc_info:
        require_admin_for_refresh(refresh=True, x_optime_admin_secret=None)
    assert exc_info.value.status_code == 403


def test_refresh_dependency_accepts_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPTIME_ADMIN_SECRET", "expected-secret")
    require_admin_for_refresh(refresh=True, x_optime_admin_secret="expected-secret")