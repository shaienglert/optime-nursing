import unittest

from app.services.facility_parameter_service import _resolve_rows_for_facility


class FacilityParameterServiceEvidenceTests(unittest.TestCase):
    def test_resolved_row_contains_evidence_records(self) -> None:
        ordered_registry = [
            {
                "parameter_id": "deficiency_count",
                "display_name": "Deficiencies",
                "family": "QUALITY_SAFETY",
                "applicable_scope": "FACILITY",
            }
        ]
        evidence_lookup = {
            "CMS-1": {
                "deficiency_count": [
                    {
                        "value": 2,
                        "source": "CMS Health Deficiencies",
                        "scope": "FACILITY",
                        "scope_name": None,
                        "last_verified": "2026-07-21T12:24:55.934Z",
                        "source_record_id": "105001",
                        "evidence_text": "Deficiency count",
                        "evidence_value": 2,
                        "evidence_date": "2026-07-21T12:24:55.934Z",
                        "confidence": "HIGH",
                        "evidence_strength": "HIGH",
                        "conflict_status": "NONE",
                        "provenance": {"source_family": "CMS"},
                    }
                ]
            }
        }
        evidence_best_lookup = {
            "CMS-1": {
                "deficiency_count": evidence_lookup["CMS-1"]["deficiency_count"][0]
            }
        }

        rows = _resolve_rows_for_facility(
            canonical_facility_id="CMS-1",
            ordered_registry=ordered_registry,
            evidence_lookup=evidence_lookup,
            evidence_best_lookup=evidence_best_lookup,
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["evidence_count"], 1)
        self.assertEqual(len(row["evidence_records"]), 1)
        self.assertEqual(row["evidence_records"][0]["source"], "CMS Health Deficiencies")


if __name__ == "__main__":
    unittest.main()
