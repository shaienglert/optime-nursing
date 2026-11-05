"""Prevent unverified facility-room claims from becoming affordability proof."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.facility_room_service import room_price_has_decision_evidence
from app.services.market_price_floor import minimum_market_monthly_price


def _room(canonical, cents, source, **kwargs):
    return SimpleNamespace(
        canonical_facility_id=canonical, room_type_name="Studio",
        monthly_price_cents=cents, pricing_qualifier="STARTING_AT",
        source=source, last_verified_at=kwargs.get("last_verified_at"),
        source_url=kwargs.get("source_url"), observed_at=kwargs.get("observed_at"),
    )


def test_self_reported_price_does_not_pass_evidence_gate():
    assert not room_price_has_decision_evidence(_room("NV-A", 10000, "OUTREACH"))
    assert not room_price_has_decision_evidence(_room("NV-A", 10000, "PROVIDER"))
    assert not room_price_has_decision_evidence(_room("NV-A", 10000, "MANUAL"))
    assert not room_price_has_decision_evidence(_room("NV-A", 10000, "RESEARCH"))
    assert not room_price_has_decision_evidence(_room(
        "NV-A", 10000, "OFFICIAL_WEBSITE", source_url="https://example.org/prices",
    ))


def test_source_linked_dated_publication_or_verified_record_passes():
    stamp = datetime(2026, 11, 5, tzinfo=timezone.utc)
    assert room_price_has_decision_evidence(_room(
        "NV-A", 400000, "OFFICIAL_WEBSITE",
        source_url="https://example.org/prices", observed_at=stamp,
    ))
    assert room_price_has_decision_evidence(_room(
        "NV-A", 400000, "PROVIDER", last_verified_at=stamp,
    ))
    assert not room_price_has_decision_evidence(_room(
        "NV-A", -100, "PROVIDER", last_verified_at=stamp,
    ))


def test_unverified_bargain_cannot_lower_market_floor():
    stamp = datetime(2026, 11, 5, tzinfo=timezone.utc)
    reported = _room("NV-CHEAP", 10000, "OUTREACH")
    sourced = _room("NV-VALID", 480000, "OFFICIAL_WEBSITE",
                    source_url="https://example.org/pricing", observed_at=stamp)
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [reported, sourced]
    with patch("app.services.market_price_floor.SessionLocal", return_value=db):
        floor = minimum_market_monthly_price(canonical_ids=["NV-CHEAP", "NV-VALID"])
    assert floor["minimum_monthly_price"] == 4800
    assert floor["canonical_facility_id"] == "NV-VALID"
    db.close.assert_called_once()


def test_only_unverified_prices_do_not_produce_a_binding_market_floor():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [
        _room("NV-CHEAP", 10000, "OUTREACH")
    ]
    with patch("app.services.market_price_floor.SessionLocal", return_value=db):
        floor = minimum_market_monthly_price(canonical_ids=["NV-CHEAP"])
    assert floor["minimum_monthly_price"] is None
    assert floor["basis"] == "NO_SOURCE_BACKED_ROOM_PRICE"
