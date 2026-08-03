from __future__ import annotations

from app.services.runtime_sync_service import get_runtime_sync_status


def test_runtime_sync_status_shape() -> None:
    status = get_runtime_sync_status()
    assert isinstance(status, dict)
    assert "dirty" in status
    assert "artifact_signature" in status
    assert "runtime_version" in status
    assert "runtime_cache" in status
    assert isinstance(status.get("recent_events"), list)
