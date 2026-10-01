from unittest.mock import patch
from app.services.market_price_floor import minimum_price_for_questionnaire

def test_price_floor_uses_selected_location_scope():
    rows={"A":{"canonical_facility_id":"A","city":"HENDERSON","latitude":36.04,"longitude":-114.98},"B":{"canonical_facility_id":"B","city":"LAS VEGAS","latitude":36.17,"longitude":-115.14}}
    with patch("app.services.facility_parameter_service.get_canonical_facility_index",return_value=rows), patch("app.services.market_price_floor.minimum_market_monthly_price",return_value={"minimum_monthly_price":3200}) as minimum:
        result=minimum_price_for_questionnaire({"locationImportant":"Yes","referenceLocationValue":"Henderson","maximumDistanceMiles":"10"})
    ids=minimum.call_args.kwargs["canonical_ids"]
    assert "A" in ids
    assert "B" not in ids
    assert result["location_scope"]["applied"] is True
