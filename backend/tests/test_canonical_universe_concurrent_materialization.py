from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

from app.services import canonical_universe


def test_concurrent_cold_start_materialization_never_fails(tmp_path: Path) -> None:
    """Reproduces the fixed-name temp-file race: 8 threads materializing the Las Vegas
    projection at once used to fail about a third of calls with FileNotFoundError."""
    target = tmp_path / "optime-nevada-las-vegas-runtime-projection-v3.json"
    errors: list[str] = []

    def materialize() -> None:
        try:
            path = canonical_universe.resolve_canonical_universe_path("las-vegas")
            assert Path(path) == target
        except Exception as exc:  # noqa: BLE001 -- collect every failure
            errors.append(f"{type(exc).__name__}: {exc}")

    with patch.object(canonical_universe, "LAS_VEGAS_RUNTIME_CACHE", target):
        for _ in range(10):
            target.unlink(missing_ok=True)
            threads = [threading.Thread(target=materialize) for _ in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

    assert errors == []
    assert target.is_file()
    assert not list(tmp_path.glob("*.tmp")), "temporary files must not be left behind"
