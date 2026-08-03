import unittest

from app.services.facility_parameter_service import _best_evidence_row, _resolve_rows_for_facility


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
            include_evidence_records=True,
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["evidence_count"], 1)
        self.assertEqual(len(row["evidence_records"]), 1)
        self.assertEqual(row["evidence_records"][0]["source"], "CMS Health Deficiencies")
        self.assertEqual(row["evidence_records"][0]["provenance"], {"source_family": "CMS"})

    def test_best_evidence_uses_scope_confidence_and_recency(self) -> None:
        rows = [
            {
                "value": "NO",
                "source": "Runtime Discovery Capability",
                "scope": "SERVICE",
                "last_verified": "2026-07-22T00:00:00Z",
                "confidence": "HIGH",
                "source_record_id": "capability:9",
                "provenance": {"source_family": "RUNTIME_DISCOVERY"},
            },
            {
                "value": "YES",
                "source": "CMS Provider Staffing",
                "scope": "SERVICE",
                "last_verified": "2026-07-20T00:00:00Z",
                "confidence": "HIGH",
                "source_record_id": "105001",
                "provenance": {"source_family": "CMS"},
            },
        ]

        best = _best_evidence_row(rows)
        self.assertEqual(best["value"], "NO")
        self.assertEqual(best["source"], "Runtime Discovery Capability")

    def test_missing_evidence_remains_unknown(self) -> None:
        ordered_registry = [
            {
                "parameter_id": "pt",
                "display_name": "Physical Therapy",
                "family": "REHABILITATION",
                "applicable_scope": "SERVICE",
            }
        ]
        rows = _resolve_rows_for_facility(
            canonical_facility_id="CMS-UNKNOWN",
            ordered_registry=ordered_registry,
            evidence_lookup={},
            evidence_best_lookup={},
            include_evidence_records=False,
        )

        self.assertEqual(rows[0]["raw_value"], "UNKNOWN")
        self.assertEqual(rows[0]["status_value"], "Not verified")
        self.assertEqual(rows[0]["source"], "Not verified")


if __name__ == "__main__":
    unittest.main()
