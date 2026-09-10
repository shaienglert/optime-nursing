from __future__ import annotations

import unittest

from app.database import Base, SessionLocal, engine
import app.models.agent_execution  # noqa: F401
import app.models.clinical_evidence  # noqa: F401
import app.models.external_discovery  # noqa: F401
from app.models.facility import Facility
from app.services.nevada_facility_scope import purge_non_nevada_facilities


class NevadaFacilityScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        self.db.query(Facility).delete()
        self.db.commit()

    def tearDown(self) -> None:
        self.db.query(Facility).delete()
        self.db.commit()
        self.db.close()

    def test_removes_only_non_nevada_facilities_and_is_idempotent(self) -> None:
        self.db.add_all([
            Facility(cms_id="NV-SCOPE-1", name="Nevada", address="1 Main", city="Las Vegas", state="NV", zip_code="89101"),
            Facility(cms_id="FL-SCOPE-1", name="Florida", address="2 Main", city="Miami", state="FL", zip_code="33101"),
        ])
        self.db.commit()

        first = purge_non_nevada_facilities(self.db)
        self.assertEqual(first["facilities_deleted"], 1)
        self.assertEqual([row.state for row in self.db.query(Facility).all()], ["NV"])
        self.assertEqual(purge_non_nevada_facilities(self.db)["facilities_deleted"], 0)
