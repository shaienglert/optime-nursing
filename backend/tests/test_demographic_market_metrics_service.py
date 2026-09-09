from __future__ import annotations

import unittest

from app.database import Base, SessionLocal, engine
from app.models.competitive_intelligence import MarketMetricObservation
from app.services.demographic_market_metrics_service import (
    collect_official_demographic_market_metrics,
    demographic_market_metrics_are_fresh,
)


def _row(year: int, base: int) -> dict[str, str]:
    row = {"NATIVITY": "1", "RACE_HISP": "0", "SEX": "0", "YEAR": str(year)}
    for age in range(86):
        row[f"POP_{age}"] = str(base + age)
    return row


class DemographicMarketMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        self.db.query(MarketMetricObservation).delete()
        self.db.commit()

    def tearDown(self) -> None:
        self.db.query(MarketMetricObservation).delete()
        self.db.commit()
        self.db.close()

    def test_collects_nevada_and_national_65_plus_and_75_plus_growth(self) -> None:
        result = collect_official_demographic_market_metrics(self.db, census_rows=[_row(2025, 100), _row(2030, 200)])
        self.assertEqual(result["observations_written"], 4)
        rows = {(row.geography_key, row.segment): row for row in self.db.query(MarketMetricObservation).all()}
        self.assertEqual(set(rows), {("NEVADA", "OLDER_ADULTS_65_PLUS"), ("NEVADA", "OLDER_ADULTS_75_PLUS"), ("NATIONAL", "OLDER_ADULTS_65_PLUS"), ("NATIONAL", "OLDER_ADULTS_75_PLUS")})
        self.assertEqual(rows[("NATIONAL", "OLDER_ADULTS_65_PLUS")].unit, "percent")
        self.assertIn("2025", rows[("NEVADA", "OLDER_ADULTS_65_PLUS")].source_scope)
        self.assertTrue(demographic_market_metrics_are_fresh(self.db))
