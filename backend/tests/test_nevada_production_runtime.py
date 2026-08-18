from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.canonical_universe import configured_canonical_market
from app.services.facility_parameter_service import (
    get_all_canonical_facility_ids,
    get_canonical_facility_index,
    get_facility_parameter_table,
    get_runtime_cache_status,
    refresh_runtime_cache,
)


class NevadaProductionRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "las-vegas"}, clear=False)
        self.env.start()
        refresh_runtime_cache("test_setup")

    def tearDown(self) -> None:
        self.env.stop()
        refresh_runtime_cache("test_teardown")

    def test_default_market_is_las_vegas_when_no_region_env_exists(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(configured_canonical_market(), "las-vegas")

    def test_runtime_contains_only_las_vegas_valley_nevada_entities(self) -> None:
        index = get_canonical_facility_index()
        ids = get_all_canonical_facility_ids()
        self.assertGreater(len(ids), 0)
        self.assertEqual(set(ids), set(index))
        self.assertTrue(all(str(row.get("state") or "").upper() == "NV" for row in index.values()))
        self.assertTrue(all(row.get("is_las_vegas_valley") is True for row in index.values()))
        self.assertFalse(any(str(row.get("state") or "").upper() == "FL" for row in index.values()))

        status = get_runtime_cache_status()
        self.assertEqual(status["market"], "las-vegas")
        self.assertEqual(status["canonical_count"], len(index))
        self.assertGreater(status["evidence_count"], 0)

    def test_assisted_living_adl_support_is_taxonomy_inference_not_invented_service_detail(self) -> None:
        index = get_canonical_facility_index()
        candidate_id = next(
            canonical_id
            for canonical_id, row in index.items()
            if row.get("canonical_type") == "ASSISTED_LIVING_RFG"
        )
        table = get_facility_parameter_table(candidate_id)
        rows = {row["parameter_id"]: row for row in table["rows"]}
        self.assertEqual(rows["adl_support"]["raw_value"], "YES")
        self.assertIn("taxonomy", rows["adl_support"]["source"].lower())
        self.assertEqual(rows["adl_support"]["evidence_strength"], "TAXONOMY_INFERRED")
        # Medication and transfer services must not be invented from RFG licensure alone.
        self.assertEqual(rows["medication_support"]["raw_value"], "UNKNOWN")
        self.assertEqual(rows["transfer_assistance"]["raw_value"], "UNKNOWN")

    def test_confirmed_memory_care_comes_from_official_nevada_detail(self) -> None:
        index = get_canonical_facility_index()
        candidate_id = next(
            canonical_id
            for canonical_id, row in index.items()
            if row.get("memory_care_classification") == "CONFIRMED"
        )
        table = get_facility_parameter_table(candidate_id)
        rows = {row["parameter_id"]: row for row in table["rows"]}
        self.assertEqual(rows["memory_care"]["raw_value"], "YES")
        self.assertIn("official detail", rows["memory_care"]["source"].lower())

    def test_skilled_nursing_uses_regulatory_identity_when_present(self) -> None:
        index = get_canonical_facility_index()
        candidate_id = next(
            canonical_id
            for canonical_id, row in index.items()
            if row.get("canonical_type") == "SKILLED_NURSING"
        )
        table = get_facility_parameter_table(candidate_id)
        rows = {row["parameter_id"]: row for row in table["rows"]}
        self.assertEqual(rows["skilled_nursing_capabilities"]["raw_value"], "YES")
        self.assertEqual(rows["nursing_24_7"]["raw_value"], "YES")


if __name__ == "__main__":
    unittest.main()
