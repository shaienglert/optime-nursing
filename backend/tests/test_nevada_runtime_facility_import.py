from __future__ import annotations

import unittest

from app.database import Base, SessionLocal, engine
from app.models.facility import Facility
from app.services.nevada_runtime_facility_import import import_las_vegas_runtime_facilities


class NevadaRuntimeFacilityImportTests(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        self.db.query(Facility).delete()
        self.db.commit()

    def tearDown(self) -> None:
        self.db.query(Facility).delete()
        self.db.commit()
        self.db.close()

    def test_imports_only_governed_nevada_valley_records(self) -> None:
        rows = [{
            "canonical_id": "NV-LIC-11168-AGC-3", "facility_name": "A and J Care Home",
            "address": "1 Main", "city": "LAS VEGAS", "state": "NV", "zip": "89101",
            "is_las_vegas_valley": True, "licensed_capacity": "7", "license_status": "Active",
        }]
        result = import_las_vegas_runtime_facilities(self.db, records=rows, source_date="2026-09-10")
        facility = self.db.query(Facility).one()
        self.assertEqual(result["facilities_created"], 1)
        self.assertEqual(facility.state, "NV")
        self.assertEqual(facility.beds, 7)
        self.assertEqual(facility.confidence_level, "HIGH")

    def test_rejects_out_of_scope_record(self) -> None:
        with self.assertRaises(ValueError):
            import_las_vegas_runtime_facilities(self.db, records=[{
                "canonical_id": "FL-1", "state": "FL", "is_las_vegas_valley": False,
            }])
