import json
import os
from collections import Counter
from unittest import mock

import pytest

from app.services.canonical_universe import resolve_canonical_universe_path
from app.services.israel_facility_import import load_israel_records
from app.services.israel_facility_registration import validate_registration

PATH = resolve_canonical_universe_path("israel-synthetic")
RECORDS = json.loads(PATH.read_text(encoding="utf-8"))["records"]
REGISTRATIONS = json.loads(PATH.with_name("registrations.json").read_text(encoding="utf-8"))["registrations"]


def test_450_clearly_synthetic_records():
    assert len(RECORDS) == 450
    for record in RECORDS:
        assert record["canonical_id"].startswith("IL-SYN-")
        assert record["facility_name"].startswith("[סינתטי]")
        assert "SYNTHETIC_TEST_DATA" in record["data_quality_flags"]
        assert record["phone"] is None and record["website"] is None


def test_every_stored_registration_is_still_valid():
    for canonical_id, payload in REGISTRATIONS.items():
        assert validate_registration(payload) == payload, canonical_id


def test_covers_every_decision_the_engine_makes():
    answers = [p["questionnaire"] for p in REGISTRATIONS.values()]
    communities = Counter(a.get("religious_character") for a in answers)
    assert {"SECULAR", "TRADITIONAL", "RELIGIOUS", "HAREDI", "MIXED", "MUSLIM", "CHRISTIAN", "DRUZE"} <= set(communities)
    for key in ("accepts_ventilated", "wandering_safe", "accepts_peg", "accepts_ng_tube"):
        values = Counter(a.get(key) for a in answers)
        assert values["YES"] and values["NO"] and values[None], key
    assert {"NO", "SAME_LEVEL", "MIXED_LEVELS"} <= {a.get("couples") for a in answers}
    assert {"MIXED", "WOMEN_ONLY", "MEN_ONLY"} <= {a.get("gender_policy") for a in answers}
    assert any(p["license_expiration_date"] < "2026-11-15" for p in REGISTRATIONS.values())
    assert len(RECORDS) - len(REGISTRATIONS) >= 10  # unregistered facilities exist


def test_real_and_synthetic_never_mix():
    with mock.patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "israel-synthetic"}):
        records, _ = load_israel_records()
    assert len(records) == 450
    with mock.patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "israel"}):
        real, _ = load_israel_records()
    assert not any(r["canonical_id"].startswith("IL-SYN-") for r in real)


def test_synthetic_registrations_seed_only_in_the_synthetic_market():
    from app.database import Base, SessionLocal, engine
    from app.models.facility import Facility, FacilityMarketRegistration
    from app.services.israel_facility_import import import_israel_facilities, seed_synthetic_registrations

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        with mock.patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "israel"}):
            with pytest.raises(RuntimeError):
                seed_synthetic_registrations(db)
        with mock.patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "israel-synthetic"}):
            import_israel_facilities(db)
            created = seed_synthetic_registrations(db)
            assert created == len(REGISTRATIONS)
            assert seed_synthetic_registrations(db) == 0  # idempotent
    finally:
        ids = [f.id for f in db.query(Facility).filter(Facility.cms_id.like("IL-SYN-%"))]
        db.query(FacilityMarketRegistration).filter(FacilityMarketRegistration.facility_id.in_(ids)).delete(synchronize_session=False)
        db.query(Facility).filter(Facility.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        db.close()
