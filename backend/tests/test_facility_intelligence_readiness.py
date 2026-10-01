from unittest.mock import patch
from app.services.facility_intelligence_readiness import facility_intelligence_readiness

def test_readiness_reports_unknown_as_unknown_not_failure():
    index={"A":{"facility_name":"A","canonical_type":"INDEPENDENT_LIVING"}}
    rows=[{"parameter_id":"adl_support","raw_value":"YES"},{"parameter_id":"current_price","raw_value":"UNKNOWN"}]
    with patch("app.services.facility_intelligence_readiness.get_canonical_facility_index",return_value=index), patch("app.services.facility_intelligence_readiness.get_facility_parameter_table",return_value={"rows":rows}):
        out=facility_intelligence_readiness()
    f=out["facilities"][0]
    assert "adl_support" in f["known_core"]
    assert "current_price" in f["unknown_core"]
    assert f["license_verified_or_not_required"] is True
