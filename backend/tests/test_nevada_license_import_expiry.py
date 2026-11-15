from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.ingestion.nevada_hcqc import _upsert_license


def _run(expiration, status="Active"):
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None
    facility = SimpleNamespace(id=1)
    row = {
        "credential_number": "NV-TEST-123",
        "credential_type_code": "AGC",
        "derived_care_type": "ASSISTED_LIVING",
        "expiration_date": expiration,
        "status": status,
    }
    _upsert_license(db, facility, row)
    return db.add.call_args.args[0]


def test_future_expiry_is_verified():
    future = (datetime.now(timezone.utc).date() + timedelta(days=30)).strftime("%m/%d/%Y")
    assert _run(future).status == "VERIFIED"


def test_expired_license_is_not_verified():
    past = (datetime.now(timezone.utc).date() - timedelta(days=1)).strftime("%m/%d/%Y")
    assert _run(past).status == "UNVERIFIED"


def test_unknown_expiry_is_not_verified():
    assert _run("UNKNOWN").status == "UNVERIFIED"


def test_inactive_license_is_not_verified():
    future = (datetime.now(timezone.utc).date() + timedelta(days=30)).strftime("%m/%d/%Y")
    assert _run(future, "Suspended").status == "UNVERIFIED"
