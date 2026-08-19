from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch


class DatabaseRuntimeTests(unittest.TestCase):
    def test_local_fallback_remains_sqlite(self):
        with patch.dict(os.environ, {}, clear=True):
            import app.database as database
            module = importlib.reload(database)
            status = module.database_runtime_status()
            self.assertEqual(status["backend"], "sqlite")
            self.assertEqual(status["durability"], "LOCAL_FALLBACK")

    def test_database_url_selects_persistent_postgres_without_exposing_secret(self):
        fake = "postgresql://user:secret@example.invalid/db"
        with patch.dict(os.environ, {"DATABASE_URL": fake}, clear=False):
            import app.database as database
            with patch("sqlalchemy.create_engine"):
                module = importlib.reload(database)
            status = module.database_runtime_status()
            self.assertEqual(status, {
                "backend": "postgresql",
                "durability": "PERSISTENT",
                "source": "DATABASE_URL",
            })
            self.assertNotIn("secret", str(status))


if __name__ == "__main__":
    unittest.main()
