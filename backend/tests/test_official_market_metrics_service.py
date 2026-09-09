from __future__ import annotations

import unittest

from app.database import Base, SessionLocal, engine
from app.models.competitive_intelligence import MarketMetricObservation
from app.services.official_market_metrics_service import cms_market_metrics_are_fresh, collect_cms_market_metrics


_PROVIDERS = [
    {"CMS Certification Number (CCN)": "100001", "State": "NV", "Number of Certified Beds": "100", "Processing Date": "2026-08-01"},
    {"CMS Certification Number (CCN)": "100002", "State": "NV", "Number of Certified Beds": "50", "Processing Date": "2026-08-01"},
    {"CMS Certification Number (CCN)": "200001", "State": "CA", "Number of Certified Beds": "75", "Processing Date": "2026-08-01"},
]

_QUALITY = [
    {"State": "NV", "Measure Description": "Percentage of residents experiencing one or more falls with major injury", "Four Quarter Average Score": "2.0", "Measure Period": "2026 Q1"},
    {"State": "NV", "Measure Description": "Percentage of residents experiencing one or more falls with major injury", "Four Quarter Average Score": "4.0", "Measure Period": "2026 Q1"},
    {"State": "CA", "Measure Description": "Percentage of residents experiencing one or more falls with major injury", "Four Quarter Average Score": "6.0", "Measure Period": "2026 Q1"},
    {"State": "NV", "Measure Description": "Number of hospitalizations per 1,000 long-stay resident days", "Four Quarter Average Score": "1.5", "Measure Period": "2026 Q1"},
    {"State": "CA", "Measure Description": "Number of hospitalizations per 1,000 long-stay resident days", "Four Quarter Average Score": "2.5", "Measure Period": "2026 Q1"},
]


class OfficialMarketMetricsServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        self.db.query(MarketMetricObservation).delete()
        self.db.commit()

    def tearDown(self) -> None:
        self.db.query(MarketMetricObservation).delete()
        self.db.commit()
        self.db.close()

    def test_collects_official_national_and_nevada_snf_metrics(self) -> None:
        result = collect_cms_market_metrics(self.db, provider_rows=_PROVIDERS, quality_rows=_QUALITY)
        self.assertEqual(result["observations_written"], 8)

        rows = {(row.metric_key, row.geography_key): row for row in self.db.query(MarketMetricObservation).all()}
        self.assertEqual(rows[("FACILITY_COUNT", "NEVADA")].value_text, "2")
        self.assertEqual(rows[("LICENSED_CAPACITY", "NEVADA")].value_text, "150")
        self.assertEqual(rows[("FACILITY_COUNT", "NATIONAL")].value_text, "3")
        self.assertEqual(rows[("LICENSED_CAPACITY", "NATIONAL")].value_text, "225")
        self.assertEqual(rows[("FALLS_MAJOR_INJURY", "NEVADA")].value_text, "3.00")
        self.assertEqual(rows[("FALLS_MAJOR_INJURY", "NATIONAL")].value_text, "4.00")
        self.assertEqual(rows[("HOSPITALIZATION_RATE", "NEVADA")].unit, "source_reported_rate")
        self.assertIn("not a population-weighted rate", rows[("HOSPITALIZATION_RATE", "NATIONAL")].source_scope)

    def test_refresh_updates_in_place_instead_of_accumulating_duplicate_snapshots(self) -> None:
        collect_cms_market_metrics(self.db, provider_rows=_PROVIDERS, quality_rows=_QUALITY)
        collect_cms_market_metrics(self.db, provider_rows=_PROVIDERS, quality_rows=_QUALITY)
        self.assertEqual(self.db.query(MarketMetricObservation).count(), 8)
        self.assertTrue(cms_market_metrics_are_fresh(self.db))


if __name__ == "__main__":
    unittest.main()
