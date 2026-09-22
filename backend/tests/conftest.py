"""Keep xdist workers from sharing the application's default SQLite database."""
import os
from pathlib import Path
import tempfile


if os.environ.get("PYTEST_XDIST_WORKER") and not os.environ.get("DATABASE_URL"):
    # Must run before test-module imports: some modules create tables at import.
    # An explicit test DATABASE_URL is still honored.
    _worker_db = Path(tempfile.mkdtemp(prefix="oomnik-pytest-")) / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{_worker_db.as_posix()}"
