from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from app.database import Base, SessionLocal, engine
from app.models.agent_execution import AgentKnowledgeRecord
from app.services.synthetic_pilot_evidence_seed import (
    SEED_AGENT_KEY,
    seed_synthetic_pilot_published_rates_evidence,
)

Base.metadata.create_all(bind=engine)


def _db():
    return SessionLocal()


class SyntheticPilotEvidenceSeedTests(unittest.TestCase):
    def tearDown(self) -> None:
        db = _db()
        try:
            db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == SEED_AGENT_KEY).delete()
            db.commit()
        finally:
            db.close()

    def test_skips_when_market_is_not_synthetic_pilot(self) -> None:
        db = _db()
        try:
            with patch("app.services.synthetic_pilot_evidence_seed.configured_canonical_market", return_value="las-vegas"):
                result = seed_synthetic_pilot_published_rates_evidence(db)
            self.assertEqual(result["status"], "SKIPPED_NOT_PILOT_MARKET")
            self.assertEqual(db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == SEED_AGENT_KEY).count(), 0)
        finally:
            db.close()

    def test_seeds_one_verified_record_per_pilot_facility(self) -> None:
        db = _db()
        try:
            with patch("app.services.synthetic_pilot_evidence_seed.configured_canonical_market", return_value="synthetic-pilot"), \
                 patch("app.services.synthetic_pilot_evidence_seed.get_all_canonical_facility_ids", return_value=["PILOT-NV-001", "PILOT-NV-002"]):
                result = seed_synthetic_pilot_published_rates_evidence(db)

            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["newly_seeded"], 2)

            rows = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == SEED_AGENT_KEY).all()
            self.assertEqual({row.entity_key for row in rows}, {"PILOT-NV-001", "PILOT-NV-002"})
            for row in rows:
                payload = json.loads(row.payload_json)
                self.assertIs(payload["published_rates_verified"], True)
                self.assertEqual(payload["market"], "las vegas")
        finally:
            db.close()

    def test_second_run_is_idempotent(self) -> None:
        db = _db()
        try:
            with patch("app.services.synthetic_pilot_evidence_seed.configured_canonical_market", return_value="synthetic-pilot"), \
                 patch("app.services.synthetic_pilot_evidence_seed.get_all_canonical_facility_ids", return_value=["PILOT-NV-001", "PILOT-NV-002"]):
                seed_synthetic_pilot_published_rates_evidence(db)
                second = seed_synthetic_pilot_published_rates_evidence(db)

            self.assertEqual(second["newly_seeded"], 0)
            self.assertEqual(second["already_seeded"], 2)
            self.assertEqual(db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == SEED_AGENT_KEY).count(), 2)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
