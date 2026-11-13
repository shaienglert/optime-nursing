from app.database import Base, SessionLocal, engine
import app.models.agent_execution  # noqa: F401
import app.models.clinical_evidence  # noqa: F401
import app.models.external_discovery  # noqa: F401
from app.services.israel_facility_page import build_israel_facility_page, list_israel_facilities


def test_every_registry_facility_has_a_uniform_page():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        items = list_israel_facilities()
        assert len(items) == 467
        keys = None
        for item in items[::40]:
            page = build_israel_facility_page(db, item["canonical_id"])
            assert page["registration_status"] in {"REGISTERED", "NOT_REGISTERED"}
            shape = (tuple(sorted(page)), tuple(sorted(page["from_list"])))
            keys = keys or shape
            assert shape == keys
        assert build_israel_facility_page(db, "IL-NOPE") is None
    finally:
        db.close()


def test_directory_filters_by_city():
    assert all("חיפה" in (i["city"] or "") for i in list_israel_facilities(city="חיפה"))
