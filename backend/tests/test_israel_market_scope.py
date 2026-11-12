from __future__ import annotations

import os
import unittest
from unittest import mock

from app.database import Base, SessionLocal, engine
import app.models.agent_execution  # noqa: F401
import app.models.clinical_evidence  # noqa: F401
import app.models.external_discovery  # noqa: F401
from app.models.facility import Facility
from app.services.israel_facility_import import import_israel_facilities, load_israel_records
from app.services.market_scope import active_state_code, is_israel_market
from app.services.nevada_facility_scope import purge_facilities_outside_state


class MarketScopeTests(unittest.TestCase):
    def test_every_market_except_israel_keeps_the_nevada_scope(self) -> None:
        for market in ("las-vegas", "nevada", "synthetic-pilot", "florida"):
            with mock.patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": market}):
                self.assertFalse(is_israel_market())
                self.assertEqual(active_state_code(), "NV")

    def test_israel_market_uses_il(self) -> None:
        for market in ("israel", "IL"):
            with mock.patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": market}):
                self.assertTrue(is_israel_market())
                self.assertEqual(active_state_code(), "IL")


class IsraelFacilityImportTests(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        self.db.query(Facility).delete()
        self.db.commit()

    def tearDown(self) -> None:
        self.db.query(Facility).delete()
        self.db.commit()
        self.db.close()

    def test_purge_then_import_leaves_only_israeli_rows_and_is_idempotent(self) -> None:
        self.db.add(Facility(cms_id="NV-SCOPE-IL", name="Nevada", address="1 Main", city="Las Vegas", state="NV", zip_code="89101"))
        self.db.commit()

        self.assertEqual(purge_facilities_outside_state(self.db, "IL")["facilities_deleted"], 1)
        first = import_israel_facilities(self.db)
        records, _ = load_israel_records()
        self.assertEqual(first["facilities_created"], len(records))
        second = import_israel_facilities(self.db)
        self.assertEqual(second["facilities_created"], 0)
        self.assertEqual(second["facilities_updated"], len(records))

        rows = self.db.query(Facility).all()
        self.assertEqual(len(rows), len(records))
        self.assertTrue(all(row.state == "IL" for row in rows))
        self.assertTrue(all(row.overall_rating is None for row in rows))
        moh = self.db.query(Facility).filter(Facility.cms_id == "IL-MOH-237U6").one()
        self.assertEqual(moh.name, "אדמונית החורש")
        self.assertEqual(moh.address, "Unknown")

    def test_rejects_out_of_scope_record(self) -> None:
        with self.assertRaises(ValueError):
            import_israel_facilities(self.db, records=[{"canonical_id": "X", "state": "NV"}])
