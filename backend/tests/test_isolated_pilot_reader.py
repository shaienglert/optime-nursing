"""Contract tests for the opt-in Neon pilot source (no network required)."""
import os
from unittest.mock import patch

import pytest

from app.services.isolated_pilot_reader import read_isolated_pilot


def test_neon_pilot_is_disabled_by_default():
    with patch.dict(os.environ, {"OOMNIK_PILOT_SOURCE": "fixture"}, clear=False):
        with pytest.raises(RuntimeError, match="not enabled"):
            read_isolated_pilot()


def test_neon_pilot_requires_separate_url():
    with patch.dict(os.environ, {
        "OOMNIK_PILOT_SOURCE": "neon",
        "DATABASE_URL": "postgresql://u:p@host/db",
        "OOMNIK_PILOT_DATABASE_URL": "postgresql://u:p@host/db",
    }, clear=False):
        with pytest.raises(RuntimeError, match="separate"):
            read_isolated_pilot()


def test_neon_pilot_rejects_non_postgres_url():
    with patch.dict(os.environ, {
        "OOMNIK_PILOT_SOURCE": "neon",
        "DATABASE_URL": "sqlite:///app.db",
        "OOMNIK_PILOT_DATABASE_URL": "sqlite:///pilot.db",
    }, clear=False):
        with pytest.raises(RuntimeError, match="PostgreSQL"):
            read_isolated_pilot()


def test_neon_pilot_reader_rejects_missing_credentials():
    with patch.dict(os.environ, {
        "OOMNIK_PILOT_SOURCE": "neon",
        "OOMNIK_PILOT_DATABASE_URL": "",
    }, clear=False):
        with pytest.raises(RuntimeError, match="separate"):
            read_isolated_pilot()


def test_neon_reader_returns_complete_mock_catalog_without_touching_app_db():
    from unittest.mock import MagicMock
    facilities = [
        {"canonical_id": f"PILOT-NV-{i:03d}", "synthetic_pilot": True}
        for i in range(1, 501)
    ]
    evidence = [{"canonical_facility_id": "PILOT-NV-001", "parameter_id": "adl_support", "value": "NO"}]
    connection = MagicMock()
    connection.execute.side_effect = [
        [(row,) for row in facilities],
        [(row,) for row in evidence],
    ]
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = connection
    with patch.dict(os.environ, {
        "OOMNIK_PILOT_SOURCE": "neon",
        "DATABASE_URL": "sqlite:///app.db",
        "OOMNIK_PILOT_DATABASE_URL": "postgresql://reader:fake@isolated.example/pilot",
    }, clear=False):
        with patch("app.services.isolated_pilot_reader.create_engine", return_value=engine):
            loaded_facilities, loaded_evidence = read_isolated_pilot()
    assert len(loaded_facilities) == 500
    assert loaded_evidence == evidence
    assert connection.execute.call_count == 2
    engine.dispose.assert_called_once()


def test_neon_reader_rejects_orphan_evidence():
    from unittest.mock import MagicMock
    facilities = [
        {"canonical_id": f"PILOT-NV-{i:03d}", "synthetic_pilot": True}
        for i in range(1, 501)
    ]
    connection = MagicMock()
    connection.execute.side_effect = [
        [(row,) for row in facilities],
        [({"canonical_facility_id": "NOT-IN-CATALOG"},)],
    ]
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = connection
    with patch.dict(os.environ, {
        "OOMNIK_PILOT_SOURCE": "neon",
        "DATABASE_URL": "sqlite:///app.db",
        "OOMNIK_PILOT_DATABASE_URL": "postgresql://reader:fake@isolated.example/pilot",
    }, clear=False):
        with patch("app.services.isolated_pilot_reader.create_engine", return_value=engine):
            with pytest.raises(RuntimeError, match="integrity"):
                read_isolated_pilot()
    engine.dispose.assert_called_once()
