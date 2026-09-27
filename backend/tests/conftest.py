"""Keep xdist workers from sharing the application's default SQLite database."""
import os
from pathlib import Path
import tempfile


if os.environ.get("PYTEST_XDIST_WORKER") and not os.environ.get("DATABASE_URL"):
    # Must run before test-module imports: some modules create tables at import.
    # An explicit test DATABASE_URL is still honored.
    _worker_db = Path(tempfile.mkdtemp(prefix="oomnik-pytest-")) / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{_worker_db.as_posix()}"


import pytest


@pytest.fixture(autouse=True)
def isolate_background_research(monkeypatch):
    """Unit tests may queue research, but must not start live daemon web research.

    Apart from unwanted network calls, surviving daemon threads read the next
    test's monkeypatched catalog and race its temporary-file assertions.
    Worker behavior itself is tested directly with controlled evidence fixtures.
    """
    from app.services import decision_agent_bridge, decision_agent_bridge_fast
    monkeypatch.setattr(decision_agent_bridge, '_kick_worker_async', lambda: None)
    monkeypatch.setattr(decision_agent_bridge_fast, '_kick_worker_async', lambda: None)
