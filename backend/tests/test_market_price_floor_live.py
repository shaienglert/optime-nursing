from datetime import datetime, timezone
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.facility_room_offering import FacilityRoomType
from app.services.market_price_floor import minimum_price_for_questionnaire


def test_floor_excludes_other_area_synthetic_and_unverified_prices():
    engine = create_engine("sqlite://")
    FacilityRoomType.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    stamp = datetime.now(timezone.utc)
    for cid, cents, verified in [("real", 400000, stamp), ("other", 100000, stamp),
                                 ("synthetic", 50000, stamp), ("unknown", 1000, None)]:
        db.add(FacilityRoomType(canonical_facility_id=cid, room_type_name="Studio",
                               monthly_price_cents=cents, last_verified_at=verified))
    db.commit()
    catalog = {"real": {"city": "Henderson"}, "other": {"city": "Las Vegas"},
               "synthetic": {"city": "Henderson", "synthetic_pilot": True},
               "unknown": {"city": "Henderson"}}
    with patch("app.services.market_price_floor.SessionLocal", factory), patch(
            "app.services.market_price_floor.get_canonical_facility_index", return_value=catalog):
        result = minimum_price_for_questionnaire({"referenceAddress": "Henderson"})
        assert result["minimum_monthly_price"] == 4000
        assert result["canonical_facility_id"] == "real"
        assert minimum_price_for_questionnaire({"referenceAddress": "Boulder City"})["minimum_monthly_price"] is None
        db.query(FacilityRoomType).delete()
        db.commit()
        assert minimum_price_for_questionnaire({"referenceAddress": "Henderson"})["minimum_monthly_price"] is None
    db.close()
