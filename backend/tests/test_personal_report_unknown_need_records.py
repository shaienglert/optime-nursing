"""The engine emits unknown critical needs as need records, not bare ids.

Before the fix the personal report raised AttributeError ('dict' has no 'replace')
for any shown candidate with an unverified critical need -- e.g. dialysis or a couple
case -- so the family got HTTP 500 instead of a report.
"""
from __future__ import annotations

from app.services import personal_decision_report_builder as builder


def _claims_for(row):
    return builder._candidate_claims(row)


def test_need_records_become_unknown_claims():
    row = {
        "canonical_facility_id": "NV-1",
        "facility_name": "Example",
        "explanation": {},
        "unknown_critical_needs": [
            {"parameter_id": "dialysis_arrangements", "requirement_level": "REQUIRED"},
            "wound_care",
        ],
    }
    texts = [claim.approved_text for claim, _section in _claims_for(row) if "has not been verified" in claim.approved_text]
    assert texts == [
        "Dialysis Arrangements has not been verified for this facility.",
        "Wound Care has not been verified for this facility.",
    ]
