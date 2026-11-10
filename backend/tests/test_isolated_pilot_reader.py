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
