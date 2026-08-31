from __future__ import annotations

import json
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.main  # noqa: F401 -- registers every model so Base.metadata.create_all resolves all FKs
from app.database import Base
from app.models.agent_execution import AgentQueueItem
from app.services.decision_agent_bridge import QUEUE_TYPE
from app.services.decision_research_worker import _priority_ordered_pending_items


class PriorityOrderedPendingItemsTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def _add(self, canonical_id: str, priority: int | None) -> None:
        payload: dict = {"canonical_facility_id": canonical_id}
        if priority is not None:
            payload["research_priority"] = priority
        self.db.add(AgentQueueItem(
            queue_type=QUEUE_TYPE,
            agent_key="provider_intelligence",
            payload_json=json.dumps(payload),
            status="PENDING",
            max_attempts=3,
        ))
        self.db.commit()

    def _ids(self, items) -> list[str]:
        return [json.loads(item.payload_json)["canonical_facility_id"] for item in items]

    def test_higher_priority_items_are_returned_first(self) -> None:
        self._add("LOW", 50)
        self._add("HIGH", 300)
        self._add("MEDIUM", 150)

        self.assertEqual(self._ids(_priority_ordered_pending_items(self.db, limit=10)), ["HIGH", "MEDIUM", "LOW"])

    def test_same_priority_items_keep_fifo_order(self) -> None:
        self._add("FIRST", 100)
        self._add("SECOND", 100)
        self._add("THIRD", 100)

        self.assertEqual(self._ids(_priority_ordered_pending_items(self.db, limit=10)), ["FIRST", "SECOND", "THIRD"])

    def test_limit_still_applies_after_sorting(self) -> None:
        self._add("LOW", 50)
        self._add("HIGH", 300)

        items = _priority_ordered_pending_items(self.db, limit=1)

        self.assertEqual(self._ids(items), ["HIGH"])

    def test_missing_or_malformed_priority_defaults_to_zero(self) -> None:
        self.db.add(AgentQueueItem(queue_type=QUEUE_TYPE, agent_key="provider_intelligence", payload_json="not json", status="PENDING", max_attempts=3))
        self.db.commit()
        self._add("HAS_PRIORITY", 10)
        self._add("NO_PRIORITY_FIELD", None)

        items = _priority_ordered_pending_items(self.db, limit=10)

        self.assertEqual(json.loads(items[0].payload_json)["canonical_facility_id"], "HAS_PRIORITY")


if __name__ == "__main__":
    unittest.main()
