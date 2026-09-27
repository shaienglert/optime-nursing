"""Structured market answers resolve location gaps only when complete."""

import pytest

from app.services.canonical_gap_policy import canonical_client_facts, gap_is_resolved


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        ({"searchState": "Nevada", "locationImportant": "No"}, True),
        ({"searchState": "Nevada"}, False),
        ({"searchState": "Nevada", "locationImportant": "Yes"}, False),
        ({"searchState": "Nevada", "locationImportant": "Yes", "referenceAddress": "89107"}, True),
        ({"searchState": "Nevada", "locationImportant": "Yes", "referenceLocationValue": "Henderson"}, True),
        ({"locationImportant": "No"}, False),
    ],
)
def test_structured_location_completeness(answers, expected):
    facts = canonical_client_facts(answers, "")
    assert facts["market_location_known"] is expected
    assert gap_is_resolved("market_location", facts) is expected


def test_free_text_city_does_not_resolve_missing_structured_market():
    facts = canonical_client_facts({}, "Please search within 15 miles of Henderson.")
    assert facts["market_location_known"] is False
